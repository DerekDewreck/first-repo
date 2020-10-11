from netmiko import ConnectHandler

cisco_881 = {
    'device_type': 'cisco_ios',
    'host':   '192.168.10.30',
    'username': 'admin',
    'password': 'cisco',
    'secret': 'cisco',     # optional, defaults to ''
}

net_connect = ConnectHandler(**cisco_881)
output = net_connect.send_command('show ip int brief')
print(output)