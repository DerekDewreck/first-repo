from ftplib import FTP

with FTP() as ftp:
    ftp.connect(host="192.168.1.204", port=21)
    ftp.login(user="cam",passwd= "cam")
    # ftp.set_pasv(True)
    ftp.cwd("array1/cam/")
    ftp.dir()
    # r.close()
    ftp.quit()


    # Changed some stuff ehre
