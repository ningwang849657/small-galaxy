' Windows 开机自启：不弹黑窗口地跑采样守护进程。
'
' 先装：  pip install small-galaxy
' 再装它：按 Win+R 输入 shell:startup 打开启动文件夹，把这个 .vbs 复制进去。
'         下次登录就会自动开始记录。
'
' 停止：  从启动文件夹删掉它，然后在任务管理器里结束 pythonw.exe。
' 手动跑一次看看： python -m smallgalaxy.lab_tracker

Set shell = CreateObject("WScript.Shell")
' pythonw.exe 没有控制台窗口；第二个参数 0 = 隐藏，第三个 False = 不等待退出。
shell.Run "pythonw.exe -m smallgalaxy.lab_tracker", 0, False
