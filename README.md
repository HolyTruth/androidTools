# androidTools
整合了一些安卓测试过程中信息搜集和批量执行的脚本，包括drozer和adb命令的批量执行、apk批量下载、空intent崩溃测试和调试activity记录。

# 功能记录
## apkUtils
apk操作相关的功能函数，不需要连接行为的功能都放这里
* apk反编译(基于jadx)
* 列出使用native方法的apk
* 获取清单文件路径
* 获取可导出的组件的相关信息
* 在反编译中查找关键字
* 在文件内容中检索私钥
## cmdUtils
基于subprocess命令执行相关的功能函数，包括Drozer和adb的命令执行
* 执行系统命令，捕获输出和报错
* 执行drozer命令
* 执行adb命令
## adbUtils
批量执行adb命令
* 获取package列表
* 下载APK(基于包名重命名)
* 返回桌面
* 检查top activity
* 启动所有activity，并截图保存至/sdcard
## drozerUtils
批量执行drozer命令， drozer的命令真的 实在是太长了
* 攻击面检查
* receiver检查
* activity检查
* service检查
* provider检查
## intentFuzz
检索清单文件中的可导出组件，发送intent，检查崩溃
* 通过logcat检查崩溃进程数量
* 对于activity，发送空action intent；对于receiver，发送空action intent和空intent
