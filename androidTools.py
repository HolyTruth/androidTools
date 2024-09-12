import os
import xml.etree.ElementTree as ET
import subprocess
import time
from colorama import init, Fore, Back, Style
import zipfile

class config:
    jadxPath = r"D:\Jadx\cli_tools\bin\jadx.bat"
    apkDownloadDir = './apks'
    decompileOutputDir = './appDecompileResult'
    drozerOutputDir = './drozerOutput'

class logUtils:
    # 日志相关的功能函数
    logPath = ''
    def info(s:str):
        s = f'[*] {s}'
        if logUtils.logPath:
            logUtils.writeToLog(s)
        print(Fore.CYAN + s + Style.RESET_ALL)

    def succ(s:str):
        s = f'[+] {s}'
        if logUtils.logPath:
            logUtils.writeToLog(s)
        print(Fore.GREEN + s + Style.RESET_ALL)

    def warn(s:str):
        s = f'[!] {s}'
        if logUtils.logPath:
            logUtils.writeToLog(s)
        print(Fore.YELLOW + s + Style.RESET_ALL)

    def fail(s:str):
        s = f'[-] {s}'
        if logUtils.logPath:
            logUtils.writeToLog(s)
        print(Fore.RED + s + Style.RESET_ALL)

    def setLogPath(logPath:str):
        # 当logPath为空时，意味着不写入log，仅打印到stdout
        # 需要保证每个类的构造函数中调用
        logUtils.logPath = logPath
        if logPath:
            with open(logUtils.logPath, 'w') as f:
                f.write('')

    def writeToLog(s:str):
        with open(logUtils.logPath, 'a') as f:
            f.write(s)

class apkUtils:
    # apk操作相关的功能函数
    # 重点是不需要adb和drozer参与
    def __init__(self, logPath = ''):
        self.jadxPath = config.jadxPath
        self.apkDir = config.apkDownloadDir
        logUtils.setLogPath(logPath)

    def apkDecompile(self, decompileDir = config.decompileOutputDir):
        """
        借助jadx工具，批量反编译指定文件夹下的所有APK（支持文件夹嵌套），输出到outputPath
        :return: null
        """
        apkPath = self.apkDir
        jadxPath = self.jadxPath

        cnt = 1
        start = time.time()
        logUtils.info("[*]Start reverse apk…")
        for path, dir_list, file_list in os.walk(apkPath):  # 反编译apkPath文件夹下所有的apk文件
            for file_name in file_list:
                if file_name.endswith('.apk'):
                    logUtils.info("*****************************************")
                    logUtils.info("[" + str(cnt) + "]" + "正在反编译的APK：" + file_name)
                    apkPath = os.path.join(path, file_name)
                    outputPath = os.path.join(decompileDir, file_name)
                    command = f'{jadxPath} -d {outputPath} -j 4 {apkPath}'
                    os.system(command)
                    cnt = cnt + 1
        end = time.time()
        logUtils.succ("[*]Done.Totally time is " + str(end - start) + "s. Enjoy it!")

    def checkNativeApk(self, decompileDir = config.decompileOutputDir) -> None:
        logUtils.info(f'正在检查使用native的apk。。。')
        for dir in os.listdir(decompileDir):
            libPath = os.path.join(decompileDir, dir, 'resources', 'lib')
            if os.path.exists(libPath):
                libList = [i[2] for i in os.walk(libPath) if '.so' in ''.join(i[2])][0]
                libArch = [i[0].split(os.path.sep)[-1] for i in os.walk(libPath) if '.so' in ''.join(i[2])]
                apkName = dir.split(os.path.sep)[-1]

                logUtils.succ(f'检测到 {apkName} ！\n\tSO：{libList} \n\tArch：{libArch}\n')

    def getManifestPath(self, packageName, decompileDir = config.decompileOutputDir):
        path = os.path.join(decompileDir, packageName + '.apk', 'resources',
                            'AndroidManifest.xml')  # .apk可能会引起BUG，所以我在这里留一行注释
        if os.path.exists(path):
            logUtils.succ(f'成功检测到 {packageName} 的清单文件！')
            return path
        logUtils.fail(f'未能检测到 {packageName} 的清单文件！尝试的路径：{path}')
        return -1

    def getExportedThing(self, packageName, decompileDir=config.decompileOutputDir) -> (list, dict):
        # 解析指定路径的清单文件
        # 返回所有exported为true的receiver和activity
        # TODO : provider service
        logUtils.info(f'正在测试 {packageName} 的 exported thing')
        path = self.getManifestPath(packageName, decompileDir)
        if path == -1:
            logUtils.warn(f'正在放弃寻找exported thing')
            return -1
        tree = ET.parse(path)
        root = tree.getroot()
        receiver = {}
        activity = []
        for child in root.iter():
            if child.tag == 'receiver' and child.attrib.get('{http://schemas.android.com/apk/res/android}exported') == 'true':
                receiverName = child.attrib.get('{http://schemas.android.com/apk/res/android}name')
                for receiverChild in child:
                    if receiverChild.tag == 'intent-filter':
                        for intentChild in receiverChild:
                            if intentChild.tag == 'action':
                                if receiver.get(receiverName) is None:
                                    receiver[receiverName] = []
                                receiver[receiverName].append(intentChild.attrib['{http://schemas.android.com/apk/res/android}name'])
                                # 相较于activity，receiver还需要获取action和receiverName的关系
            elif child.tag == 'activity' and child.attrib.get('{http://schemas.android.com/apk/res/android}exported') == 'true':
                activityName = child.attrib['{http://schemas.android.com/apk/res/android}name']
                activity.append(activityName)
        logUtils.succ(f'解析成功：\n\tAcitivity：{activity}\n\tReceiver：{receiver}')
        return (activity, receiver)

    def searchInDecompile(self, keyList, dir = config.decompileOutputDir):
        logUtils.info(f'正在检索 {keyList} ...')
        fileCnt = 0
        contentCnt = 0
        for curDir, dirs, files in os.walk(dir):
            for file in files:
                res = []
                filePath = os.path.join(curDir, file)
                with open(filePath, 'rb') as f:
                    for line in f.readlines():
                        if any([key in line for key in keyList]):
                            res.append(line.decode())
                if res:
                    fileCnt += 1
                    contentCnt += len(res)
                    logUtils.succ(f'在 {filePath} 检测到关键字：\n\t{'\n\t'.join(res)}')
        if fileCnt:
            logUtils.succ(f'在 {fileCnt} 个文件中发现 {contentCnt} 个关键字！')
        else:
            logUtils.fail(f'未发现关键字：{keyList}')
    def checkPrivateKey(self):
        keyList = [b'-----BEGIN', b'-----\\n']
        self.searchInDecompile(keyList)

class cmdUtils:
    # 命令执行相关的功能函数，包括Drozer和adb的命令执行
    def runCmd(cmd:str):
        # return subprocess.run(cmd, shell=True, text=True, capture_output=True).stdout
        logUtils.info(f'正在执行:\n\t{cmd}')

        process = subprocess.Popen(cmd, shell=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        res = stdout + stderr

        logUtils.info(f'执行结果：\n\t{res.strip().replace('\n', '\n\t')}')
        return res

    def runDrozerCmd(cmd:str):
        cmd = 'drozer console connect -c "%s"' % cmd
        return cmdUtils.runCmd(cmd)

    def runADBCmd(cmd:str):
        cmd = 'adb shell "%s"' % cmd
        return cmdUtils.runCmd(cmd)

class adbUtils:
    # 会用到adb命令的功能函数集合
    # 前置为adb功能正常，且连接正常
    packageList = []
    def __init__(self, logPath = ''):
        logUtils.setLogPath(logPath)
        self.packageList = self.getPackageList()

    def getPackageList(self):
        # 获取所有APP
        logUtils.info('正在获取app列表。。。')
        appList = cmdUtils.runADBCmd('pm list package').replace('package:', '').strip().split('\n')
        logUtils.succ(appList)
        logUtils.succ(f'读取到 {len(appList)} 个app！')
        return appList

    def downloadPackage(self, packageName):
        logUtils.info(f'正在下载：{packageName}')
        if not os.path.exists(config.apkDownloadDir):
            os.mkdir(config.apkDownloadDir)

        packagePath = cmdUtils.runADBCmd(f'pm path {packageName}').strip().replace('package:', '')
        cmdUtils.runCmd(f'adb pull {packagePath} {os.path.join(config.apkDownloadDir, packageName)}.apk')
        logUtils.info(f'package与apk名的映射：{packageName} -> {packagePath.split('/')[-1]}')

        # copy in windows and cp in linux
        # res = runCmd(f'copy .\\apps\\{appPath.split('/')[-1]} .\\apps\\{appName}.apk').strip()

        # info(f'copying ./apps/{appPath.split('/')[-1]} to ./apps/{appName}.apk; res = {res}')

    def downloadAllPackage(self):
        logUtils.info('正在下载所有Package。。。')
        for packageName in self.packageList:
            self.downloadPackage(packageName)

    def backToHome(self):
        logUtils.info('正在回到桌面。。。')
        cmdUtils.runADBCmd('am start -W -a android.intent.action.MAIN -c android.intent.category.HOME')

    def checkTopActivity(self, packageName) -> int:
        # 检查执行状态
        logUtils.info(f'正在检查顶部activity是否为{packageName}')
        res = cmdUtils.runADBCmd('dumpsys activity activities | grep VisibleActivity').strip()

        return packageName in res

    def recordEveryActivity(self):
        # 将所有可导出的Activity启动，并截图记录
        # 前提：/sdcard/有权写入
        tmpPicPath = '/sdcard/aaaaaaaaaaaPicTmp'
        cmdUtils.runADBCmd(f'mkdir {tmpPicPath}')
        # apkUtil = apkUtils()
        cnt = 1
        for packageName in self.packageList:
            try:
                activityList, _ = apkUtils.getExportedThing(packageName)
            except Exception as e:
                logUtils.fail('解析清单文件报错：')
                logUtils.fail(e)
                continue
            for activity in activityList:
                cmd = f'am start -W -n {packageName}/{activity}'
                cmdUtils.runADBCmd(cmd)
                if self.checkTopActivity(packageName):
                    time.sleep(2)
                    logUtils.succ(f'{packageName}/{activity} 启动成功，正在截图！')
                    picPath = f'{tmpPicPath}/{cnt}.png'
                    cmdUtils.runADBCmd(f'screencap -p {picPath}')
                    self.backToHome()
                    cnt += 1
                    logUtils.succ(f'已将 {packageName}/{activity} 保存到 {picPath}')

        cmdUtils.runCmd(f'adb pull {tmpPicPath} ./activityRecord')
        logUtils.succ(f'已将截图下载到本地：./activityRecord ； 应下数量 {cnt} ；实下数量 {int(cmdUtils.runADBCmd(f'ls {tmpPicPath} | wc -l').strip())}')
        cmdUtils.runADBCmd(f'rm -rf {tmpPicPath}')

class drozerUtils:
    # drozer相关的功能函数集合
    # 前置：
    #   adb功能正常
    #   drozer代理app已安装且启动
    #   没有其他客户端正在使用drozer
    #   adbUtils类已初始化


    def __init__(self, logPath = ''):
        logUtils.setLogPath(logPath)
        if adbUtils.packageList == []:
            logUtils.fail('adbUtils.packageList为空，adbUtils未初始化！')
            exit(0)

    def checkAtk(self):
        # 攻击面检查
        logUtils.info(f'正在进行攻击面(attacksurface)检查')
        atkLogPath = os.path.join(config.drozerOutputDir,'atk.txt')
        with open(atkLogPath, 'w') as f:
            for packageName in adbUtils.packageList:
                res = cmdUtils.runDrozerCmd(f'run app.package.attacksurface {packageName}')
                f.write(f'--------------------------{packageName}------------------------\n')
                f.write(res + '\n')
                logUtils.succ(f'{packageName}: {res}')

    def checkActivity(self):
        # activity检查
        logUtils.info('正在进行Activity检查。。。')
        activityLogPath = os.path.join(config.drozerOutputDir,'activity.txt')
        with open(activityLogPath, 'w') as f:
            for packageName in adbUtils.packageList:
                res = cmdUtils.runDrozerCmd(f'run app.activity.info -a {packageName}')
                if 'No matching activities.' in res or 'could not find the package' in res:
                    continue
                f.write(f'--------------------------{packageName}------------------------\n')
                f.write(res + '\n')
                logUtils.succ(f'{packageName}: {res}')

    def checkReceiver(self):
        # 显式intent检查，过滤无receiver的app
        logUtils.info(f'正在进行broadcast receiver审计。。。')
        receiverLogPath = os.path.join(config.drozerOutputDir,'receiver.txt')
        with open(receiverLogPath, 'w') as f:
            for packageName in adbUtils.packageList:
                res = cmdUtils.runDrozerCmd(f'run app.broadcast.info -a {packageName}')
                if 'No matching receivers.' in res or 'could not find the package' in res:
                    continue
                f.write(f'--------------------------{packageName}------------------------\n')
                f.write(res+'\n')
                logUtils.succ(f'{packageName}: {res}')

    def checkService(self):
        # service检查，过滤无service的app
        logUtils.info('正在进行service攻击面审计。。。')
        serviceLogPath = os.path.join(config.drozerOutputDir,'service.txt')
        with open(serviceLogPath,'w') as f:
            for packageName in adbUtils.packageList:
                res = cmdUtils.runDrozerCmd(f'run app.service.info -a {packageName}')
                if 'No exported services.' in res or 'could not find the package' in res:
                    continue
                f.write(f'--------------------------{packageName}------------------------\n')
                f.write(res+'\n')
                logUtils.succ(f'{packageName}: {res}')

    def checkProvider(self):
        # activity检查
        logUtils.info('正在进行provider审计。。。')
        providerLogPath = os.path.join(config.drozerOutputDir,'provider.txt')
        with open(providerLogPath, 'w') as f:
            for packageName in adbUtils.packageList:
                res = cmdUtils.runDrozerCmd(f'run app.provider.info -a {packageName}')
                if 'No matching providers.' in res or 'could not find the package' in res:
                    continue
                f.write(f'--------------------------{packageName}------------------------\n')
                f.write(res + '\n')
                logUtils.succ(f'{packageName}: {res}')

    def checkAll(self):
        self.checkAtk()
        self.checkReceiver()
        self.checkService()
        self.checkActivity()
        self.checkProvider()

class intentFuzz:
    pocList = []
    def __init__(self, logPath = ''):
        logUtils.setLogPath(logPath)


    def getCrashCnt(self):
        return int(cmdUtils.runADBCmd('logcat -b crash  -d | grep Process: | wc -l').strip())

    def intentFuzz(self):
        # activity
        # receiver
        beforeFuzzCrashCnt = self.getCrashCnt()
        for packageName in adbUtils.packageList:
            logUtils.info(f"--------------------------------{packageName}-------------------------------------")
            activityList, receiverDict = apkUtils.getExportedThing(packageName)

            # Activity fuzz

            # activityList = qdAnalyse.getExportedActivity(packageName)
            for activity in activityList:
                cmd = f'am start -W -n {packageName}/{activity}'
                tmpCnt = self.getCrashCnt()
                cmdUtils.runADBCmd(cmd)
                time.sleep(1)
                if self.getCrashCnt() != tmpCnt:
                    logUtils.succ(f'新增 {self.getCrashCnt() - tmpCnt} 个Crash！')
                    self.pocList.append(cmd)

            # receiver fuzz
            for receiver in receiverDict:
                for action in receiverDict[receiver]:
                    # 空参数测试
                    cmd = f'am broadcast -W -n {packageName}/{receiver} -a {action}'
                    tmpCnt = self.getCrashCnt()
                    cmdUtils.runADBCmd(cmd)
                    time.sleep(1)
                    if self.getCrashCnt() != tmpCnt:
                        logUtils.succ(f'新增 {self.getCrashCnt() - tmpCnt} 个Crash！')
                        self.pocList.append(cmd)

                    # 空action
                    cmd = f'am broadcast -W -n {packageName}/{receiver}'
                    tmpCnt = self.getCrashCnt()
                    cmdUtils.runADBCmd(cmd)
                    time.sleep(1)
                    if self.getCrashCnt() != tmpCnt:
                        logUtils.succ(f'新增 {self.getCrashCnt() - tmpCnt} 个Crash！')
                        self.pocList.append(cmd)
        logUtils.succ('poc list ：\n\t' + '\n\t'.join(self.pocList))

        logUtils.succ(f'成功触发并检测到 {self.getCrashCnt() - beforeFuzzCrashCnt} 个崩溃！')
        logUtils.succ(f'上述崩溃命令 {len(self.pocList)} 条！')

if __name__ == '__main__':
    apkUtils = apkUtils()
    packageName = 'com.test'
    adbUtils = adbUtils()
    adbUtils.recordEveryActivity()
    # apkUtils.getExportedThing(packageName)
