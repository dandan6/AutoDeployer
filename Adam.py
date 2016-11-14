import subprocess
from subprocess import Popen,PIPE,STDOUT
import time
import pyVmomi
from paramiko import client
from pyVim.connect import Disconnect, SmartConnect, GetSi
import socket
import ssl
import sys
import os
import unicodedata
import tkinter as tk
from tkinter import filedialog
import datetime
import csv
import ssl
import sys
import unicodedata
from selenium import webdriver
from selenium import *
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import NoAlertPresentException
import unittest, time, re
import os
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

clusterSelected = 0 #Chosen cluster
dsSelected = 0 #Chosen cluster
vlanSelected = 0
versionSelect = 0
clusterNum = 1 #Cluster Number (equal to the vCenter list)
esx = [] #List of ESXs per cluster (for updating lists and dictionary) - deleted every time after passing info
clusterDictESX = dict() #Cluster Number (equal to the vCenter list) with ESXs under it
ds = []
clusterDictDS = dict()
vlan = []
clusterDictVlan = dict()
mobOVA = [] #Contain the names for each compnent for cluster hierarchy (dataCenter.cluster.folder.host)
mobLocation = [] #Exact location in mob for each cluster
rpaNum = 0 #Total RPAs to deploy
rpaNameList = [] #RPAs Name list
rpaIpList = [] #RPAs IP list
rpaLength = 0 #RPA deployment per ESX (mark the position in rpaIpList and run on all the array)
build = None #Logger position for OVA file
buildsPath = '\\\\rpsmbgw.lss.emc.com\\'
ova = '' #Direct path from pc for OVA location
ovaBuild = 0 #User build selection
selectedDHCP = 0
DHCP = False
deployType = 0
deployFile = 0
file_path = ''

IpDHCP = '0.0.0.0'
netmaskStatic = '255.255.254.0'
lanLocalGW = '10.76.10.1'
lanRemoteGW = '10.76.16.1'



#==============#
#     FUNC     #
#==============#

class ssh: #Allow to connect and enable to send SSH command
    client = None
    def __init__(self,address,username,password):
        try:
            print('Connecting to server {}'.format(address))
            self.client = client.SSHClient()
            self.client.set_missing_host_key_policy(client.AutoAddPolicy())
            self.client.connect(address,username=username,password=password,look_for_keys=False)
        except TimeoutError:
            sys.exit('The server is unreachable!')
    def closeConnection(self):
        self.client.close()
    def sendCommand(self,command):
        if(self.client):
            stdin,stdout,stderr = self.client.exec_command(command)
            while not stdout.channel.exit_status_ready():
                if stdout.channel.recv_ready():
                    alldata = stdout.channel.recv(1024)
                    prevdata = b"1"
                    while prevdata:
                        prevdata = stdout.channel.recv(1024)
                        alldata += prevdata
                    return(str(alldata, "utf8"))
        else:
            print('Connection not opened.')

def checkIp(ip): #Check ip address structure
    list = ip.split('.')
    if len(list) != 4:
        return False
    for i in list:
        try:
            int(i)
        except ValueError:
            return False
        if int(i) < 0 or int(i) > 255:
            return False
    return True

def pingCheck(ip):
    global status
    status,result = sp.getstatusoutput("ping -n 1 " + str(ip))
    if status == 0:
        return True
    else:
        return False

def connectVC(ip):
    inputs = {'vcenter_password': 'Kashya123!',
              'vcenter_user': r"administrator@vsphere.local",
              }
    try:
        #default_context = ssl._create_default_https_context
        ssl._create_default_https_context = ssl._create_unverified_context
        print ("Connecting to vCenter server: {}".format(ip))
        si = SmartConnect(host=ip, user=inputs['vcenter_user'], pwd=inputs['vcenter_password'])
        return si
        #return connect
    except:
        try:
            si = SmartConnect(host=ip, user="root", pwd="Kashya123!")
            return si
        except:
            try:
                si = SmartConnect(host=ip, user="root", pwd="vmware")
                return si
            except:
                print ("VC is down")

def getGateway(ip):  # check 3rd octet and return GW with Netmask
    list = ip.split('.')
    if (list[2]) == '10' or (list[2]) == '11':
        return lanLocalGW
    elif (list[2]) == '16' or (list[2]) == '17':
        return lanRemoteGW
    else:
        return False

def normalize_caseless(text): #Make all Upper letter in a string to be lower
    return unicodedata.normalize("NFKD", text.casefold())
def caseless_equal(left, right):
    return normalize_caseless(left) == normalize_caseless(right)

def selectBuild(build):
    print('RecoverPoint Version:\n[1] 5.0\n[2] 5.0.1')  # Check if installation will be Static or DHCP
    try:
        versionSelect = int(input('Choose the version for deployment: '))
    except:
        ValueError
    while versionSelect not in range(1, 3):
        try:
            versionSelect = int(input('Your selection is not from the list, Please select again: '))
        except:
            ValueError
    print()
    if versionSelect == 1:
        while build == None:  # Cluster build choosing taken from logger
            try:
                logger = ssh('10.76.66.65', 'sr',
                             'kashya')  # get Latest Hawaii 5.0 Build asd choose the build for deploy
                latestBuild = logger.sendCommand('ls -rt /mnt/builds | grep -F rel5.0_d. | tail -1 | cut -f3 -d.')
                ovaBuild = input("Enter a valid RP build for Hawaii 5.0 (Default '{}'): ".format(latestBuild[
                                                                                                 :-1]))  # get 5.0 build and make it available for Linux user account (ILCOE user must have it!)
                if ovaBuild == '':
                    ovaBuild = latestBuild[:-1]
                build = logger.sendCommand(
                    'find /mnt/builds/rel5.0_d.{}/emc/ -name "*.ova" | grep RP4VM'.format(ovaBuild))
                if build == None:
                    build = logger.sendCommand('find /mnt/builds/rel5.0_d.{}/emc/ -name "*.ova"'.format(ovaBuild))
                if build == None:
                    print('Build not found!\n')
            except:
                TypeError
    elif versionSelect == 2:
        while build == None:  # Cluster build choosing taken from logger
            try:
                logger = ssh('10.76.66.65', 'sr',
                             'kashya')  # get Latest Hawaii 5.0 Build asd choose the build for deploy
                latestBuild = logger.sendCommand('ls -rt /mnt/builds | grep -F rel5.0.SP1_e. | tail -1 | cut -f4 -d.')
                ovaBuild = input("Enter a valid RP build for Hawaii 5.0.1 (Default '{}'): ".format(latestBuild[
                                                                                                   :-1]))  # get 5.0 build and make it available for Linux user account (ILCOE user must have it!)
                if ovaBuild == '':
                    ovaBuild = latestBuild[:-1]
                build = logger.sendCommand(
                    'find /mnt/builds/rel5.0.SP1_e.{}/emc/ -name "*.ova" | grep RP4VM'.format(ovaBuild))
                if build == None:
                    build = logger.sendCommand('find /mnt/builds/rel5.0.SP1_e.{}/emc/ -name "*.ova"'.format(ovaBuild))
                if build == None:
                    print('Build not found!\n')
            except:
                TypeError
    ova = buildsPath + build[5:]
    logger.closeConnection()
    return ova

def analys_OVF(ovf_file):
    print (ovf_file)
    netlist = []
    os.path.join('C:', '\\', 'Program Files', 'VMware', 'VMware OVF Tool')
    os.chdir('C:\\Program Files\\VMware\\VMware OVF Tool')
    out = Popen([r'ovftool.exe', '--hideEula', ovf_file],stdout=PIPE, stderr=STDOUT)
    #t  = subprocess.call([r'ovftool.exe', '--hideEula', ovf_file])
    t = out.communicate()[0]
    if os.path.exists('ovf.txt'):
        os.remove('ovf.txt')
        file = open('ovf.txt', 'a')
        file.close()
    else:
        file = open('ovf.txt', 'a')
        file.close()
    if os.path.exists('networks.txt'):
        os.remove('networks.txt')
        file = open('networks.txt', 'a')
        file.close()
    else:
        file = open('networks.txt','a')
        file.close()
    with open('ovf.txt', 'r+') as file:
        file.writelines(t.decode())
    with open('ovf.txt','r+') as infile,open('networks.txt', 'w')as outfile:
        copy = False
        for line in infile:
            if line.strip() == "Networks:":
                copy = True
            elif line.strip() == "Virtual Machines:":
                copy = False
            elif copy:
                outfile.write(line)
    with open('networks.txt','r') as netfile:
        for line in netfile:
            if "Name:" in line:
                net = line.split("Name:")[1].strip()
                netlist.append(net)
    return netlist

def Deploy_RPAs(name, ds, net, VLAN, ip, netmask, gateway, ova_file, path):
    command = r'ovftool.exe --acceptAllEulas --lax  --skipManifestCheck --noSSLVerify --name=%s --coresPerSocket:"vRPA"="4"  --ipProtocol="IPv4" -ds="%s" --powerOn  --net:"%s"="%s" --prop:ip="%s" --prop:netmask="%s" --prop:gateway="%s"  "%s" "%s"' % (
            name, ds, net, VLAN, ip, netmask, gateway, ova_file, path)
    #print(command)
    return command

def enableRemoteConnection(vm,si): #Change RPA pass to q and configure SSH remote connection
    rootAdmin = pyVmomi.vim.vm.guest.NamePasswordAuthentication(username='root', password='q')
    root4 = pyVmomi.vim.vm.guest.NamePasswordAuthentication(username='root', password='Sl&t4atf')
    root5 = pyVmomi.vim.vm.guest.NamePasswordAuthentication(username='root', password='NiT6^MoM')
    passChange1 = pyVmomi.vim.vm.guest.ProcessManager.ProgramSpec(arguments="-i -e 's/PermitRootLogin no/PermitRootLogin yes/g' /etc/ssh/sshd_config", programPath="/bin/sed")
    passChange2 = pyVmomi.vim.vm.guest.ProcessManager.ProgramSpec(arguments="-i -e 's/DenyUsers/#DenyUsers/g' /etc/ssh/sshd_config", programPath="/bin/sed")
    passChange3 = pyVmomi.vim.vm.guest.ProcessManager.ProgramSpec(arguments="ssh restart", programPath="/usr/sbin/service")
    qChange = pyVmomi.vim.vm.guest.ProcessManager.ProgramSpec(arguments="root:q | /usr/sbin/chpasswd", programPath="/bin/echo")
    print('Remote connection is currently disabled')
    print('Enable remote connection...')
    try:
        si.content.guestOperationsManager.processManager.StartProgramInGuest(vm=vm, auth=rootAdmin, spec=passChange1)
        si.content.guestOperationsManager.processManager.StartProgramInGuest(vm=vm, auth=rootAdmin, spec=passChange2)
        si.content.guestOperationsManager.processManager.StartProgramInGuest(vm=vm, auth=rootAdmin, spec=passChange3)
        print("Current password is 'q'")
    except:
        try:
            si.content.guestOperationsManager.processManager.StartProgramInGuest(vm=vm, auth=root4, spec=passChange1)
            si.content.guestOperationsManager.processManager.StartProgramInGuest(vm=vm, auth=root4, spec=passChange2)
            si.content.guestOperationsManager.processManager.StartProgramInGuest(vm=vm, auth=root4, spec=passChange3)
            si.content.guestOperationsManager.processManager.StartProgramInGuest(vm=vm, auth=root4, spec=qChange)
            print("Current password is 'Sl&t4atf'")
        except:
            si.content.guestOperationsManager.processManager.StartProgramInGuest(vm=vm, auth=root5, spec=passChange1)
            si.content.guestOperationsManager.processManager.StartProgramInGuest(vm=vm, auth=root5, spec=passChange2)
            si.content.guestOperationsManager.processManager.StartProgramInGuest(vm=vm, auth=root5, spec=passChange3)
            si.content.guestOperationsManager.processManager.StartProgramInGuest(vm=vm, auth=root5, spec=qChange)
            print("Current password is 'NiT6^MoM'")
    print ('Configure remote connection succeeded.')





#==================================#
#               MAIN               #
#==================================#


print(" ___           _           _____   ___    ")
print("|   \ ___ _ __| |___ _  _ / _ \ \ / /_\\  ")
print("| |) / -_) '_ \ / _ \ || | (_) \ V / _ \\ ")
print("|___/\___| .__/_\___/\_, |\___/ \_/_/ \_\\   Ver_1.0")
print("=========|_|=========|__/==========================\n")

print('Deployment:\n[1] Deploy OVA\n[2] DGUI - Install a vRPA cluster\n[3] Full Deployment ( Deploy OVA + DGUI )')
try:
    deployType = int(input('Please select the type of deployment (1-3): '))
except:
    ValueError
while deployType not in range (1,4):
    try:
        deployType = int(input('Your selection is not from the list, Please select again: '))
    except:
        ValueError
print()




#==============#
#  Deploy OVA  #
#==============#

if deployType == 1 or deployType == 3 : #Deploy OVA menu
    print('Deploy OVA:\n[1] Manual\n[2] Import from file')
    try:
        deployFile = int(input('Please select how to deploy OVA (1-2): '))
    except:
        ValueError
    while deployFile not in range(1, 3):
        try:
            deployFile = int(input('Your selection is not from the list, Please select again: '))
        except:
            ValueError
    print('\n---------------------------------------------------\n')





    # ======================= Deploy OVA: Manual =======================

    if deployFile == 1:
        vcIp = input('Please insert vCenter IP: ')  # get VC and check the connection
        while not checkIp(vcIp):
            vcIp = input('vCenter IP is not valid, please insert vCenter IP: ')
        connectVC(vcIp)
        # vc = ssh(vcIp,'administrator@vsphere.local','Kashya123!')
        # vc.closeConnection()

        print('\nClusters list:')  # Choose a cluster and get ESXs under it via mobOVA
        default_context = ssl._create_default_https_context
        ssl._create_default_https_context = ssl._create_unverified_context
        inputs = {'vcenter_password': 'Kashya123!', 'vcenter_user': r"administrator@vsphere.local"}
        si = SmartConnect(host=vcIp, user=inputs['vcenter_user'], pwd=inputs['vcenter_password'])
        content = si.RetrieveContent()
        for dataCenter in range(0, len(content.rootFolder.childEntity)):  # Cluster
            for cluster in range(0, len(content.rootFolder.childEntity[dataCenter].hostFolder.childEntity)):
                if 'domain' not in str(content.rootFolder.childEntity[dataCenter].hostFolder.childEntity[cluster]):
                    for folder in range(0, len(
                            content.rootFolder.childEntity[dataCenter].hostFolder.childEntity[cluster].childEntity)):
                        for host in range(0, len(
                                content.rootFolder.childEntity[dataCenter].hostFolder.childEntity[cluster].childEntity[
                                    folder].host)):
                            esx.append(
                                content.rootFolder.childEntity[dataCenter].hostFolder.childEntity[cluster].childEntity[
                                    folder].host[host].name)
                            # esx.append(socket.gethostbyname(content.rootFolder.childEntity[dataCenter].hostFolder.childEntity[cluster].childEntity[folder].host[host].name))
                        if esx != []:
                            for datastore in range(0, len(
                                    content.rootFolder.childEntity[dataCenter].hostFolder.childEntity[
                                        cluster].childEntity[folder].datastore)):
                                if content.rootFolder.childEntity[dataCenter].hostFolder.childEntity[
                                    cluster].childEntity[folder].datastore[
                                    datastore].summary.multipleHostAccess == True:
                                    ds.append(content.rootFolder.childEntity[dataCenter].hostFolder.childEntity[
                                                  cluster].childEntity[folder].datastore[datastore].name)
                            for network in range(0, len(
                                    content.rootFolder.childEntity[dataCenter].hostFolder.childEntity[
                                        cluster].childEntity[folder].network)):
                                vlan.append(content.rootFolder.childEntity[dataCenter].hostFolder.childEntity[
                                                cluster].childEntity[folder].network[network].name)
                            print('[{}] {}'.format(clusterNum,
                                                   content.rootFolder.childEntity[dataCenter].hostFolder.childEntity[
                                                       cluster].childEntity[folder].name))
                            mobOVA.append('{}/{}/{}/{}'.format(content.rootFolder.childEntity[dataCenter].name,
                                                               content.rootFolder.childEntity[
                                                                   dataCenter].hostFolder.name,
                                                               content.rootFolder.childEntity[
                                                                   dataCenter].hostFolder.childEntity[cluster].name,
                                                               content.rootFolder.childEntity[
                                                                   dataCenter].hostFolder.childEntity[
                                                                   cluster].childEntity[folder].name))
                            mobLocation.append(
                                'content.rootFolder.childEntity[{}].hostFolder.childEntity[{}].childEntity[{}]'.format(
                                    dataCenter, cluster, folder))
                            clusterDictESX.update({clusterNum: esx})
                            clusterDictDS.update({clusterNum: ds})
                            clusterDictVlan.update({clusterNum: vlan})
                            esx = []
                            ds = []
                            vlan = []
                            clusterNum += 1
                else:
                    for host in range(0, len(
                            content.rootFolder.childEntity[dataCenter].hostFolder.childEntity[cluster].host)):
                        esx.append(
                            content.rootFolder.childEntity[dataCenter].hostFolder.childEntity[cluster].host[host].name)
                        # esx.append(socket.gethostbyname(content.rootFolder.childEntity[dataCenter].hostFolder.childEntity[cluster].childEntity[folder].host[host].name))
                    if esx != []:
                        for datastore in range(0, len(
                                content.rootFolder.childEntity[dataCenter].hostFolder.childEntity[cluster].datastore)):
                            if content.rootFolder.childEntity[dataCenter].hostFolder.childEntity[cluster].datastore[
                                datastore].summary.multipleHostAccess == True:
                                ds.append(content.rootFolder.childEntity[dataCenter].hostFolder.childEntity[
                                              cluster].datastore[datastore].name)
                        for network in range(0, len(
                                content.rootFolder.childEntity[dataCenter].hostFolder.childEntity[cluster].network)):
                            vlan.append(
                                content.rootFolder.childEntity[dataCenter].hostFolder.childEntity[cluster].network[
                                    network].name)
                        print('[{}] {}'.format(clusterNum,
                                               content.rootFolder.childEntity[dataCenter].hostFolder.childEntity[
                                                   cluster].name))
                        mobOVA.append('{}/{}/{}'.format(content.rootFolder.childEntity[dataCenter].name,
                                                        content.rootFolder.childEntity[dataCenter].hostFolder.name,
                                                        content.rootFolder.childEntity[
                                                            dataCenter].hostFolder.childEntity[cluster].name))
                        mobLocation.append(
                            'content.rootFolder.childEntity[{}].hostFolder.childEntity[{}]'.format(dataCenter, cluster))
                        clusterDictESX.update({clusterNum: esx})
                        clusterDictDS.update({clusterNum: ds})
                        clusterDictVlan.update({clusterNum: vlan})
                        esx = []
                        ds = []
                        vlan = []
                        clusterNum += 1
        try:
            clusterSelected = int(input('Enter the cluster number for deploy OVA: '))
        except:
            ValueError
        while clusterSelected == '' or clusterSelected < 1 or clusterSelected >= clusterNum or clusterDictESX.get(
                clusterSelected) == []:
            try:
                clusterSelected = int(input('Your selection is not from the list, Please select again: '))
            except:
                ValueError
        print()

        ova = selectBuild(build) #RP version and build
        print()

        print('IP Address Allocation:\n[1] Static\n[2] DHCP')  # Check if installation will be Static or DHCP
        try:
            selectedDHCP = int(input('Choose the IP allocation policy to use: '))
        except:
            ValueError
        while selectedDHCP not in range(1, 3):
            try:
                selectedDHCP = int(input('Your selection is not from the list, Please select again: '))
            except:
                ValueError
        if selectedDHCP == 2:
            DHCP = True
        print()

        print('Network Mapping:')  # vlan selection choosing by spec
        for network in range(0, len(clusterDictVlan[clusterSelected])):
            # if normalize_caseless("lan") in normalize_caseless(clusterDictVlan[clusterSelected][network]) and normalize_caseless("wan") not in normalize_caseless(clusterDictVlan[clusterSelected][network]) \
            # and (normalize_caseless("8") in normalize_caseless(clusterDictVlan[clusterSelected][network])
            # or normalize_caseless("9") in normalize_caseless(clusterDictVlan[clusterSelected][network])):
            vlan.append(clusterDictVlan[clusterSelected][network])
            print('[{}] {}'.format(vlan.index(clusterDictVlan[clusterSelected][network]) + 1,
                                   clusterDictVlan[clusterSelected][network]))
        try:
            vlanSelected = int(input('Enter the LAN management network: '))
        except:
            ValueError
        while vlanSelected < 1 or vlanSelected > len(vlan):
            try:
                vlanSelected = int(input('Your selection is not from the list, Please select again: '))
            except:
                IndexError
        # print(vlan[vlanSelected-1])
        print()

        try:
            rpaNum = int(input('Enter the total number of RPAs under this cluster (1-8): '))
        except:
            ValueError
        while rpaNum < 1 or rpaNum > 8:  # get the total RPAs to deploy - Name & IP
            try:
                rpaNum = int(input('Your selection is not in range (1-8), Please select again: '))
            except:
                ValueError
        for rpa in range(0, rpaNum):
            name = input('\nEnter RPA {} name: '.format(rpa + 1))
            while name in rpaNameList or name == '' or ' ' in name:
                name = input('Name is not valid or already exist, Enter RPA {} name: '.format(rpa + 1))
            rpaNameList.append(name)
            if DHCP == True:  # DHCP configuration per RPA
                ip = netmask = gateway = IpDHCP
                rpaIpList.append(ip)
            else:
                netmask = netmaskStatic
                ip = input('Enter RPA {} IP: '.format(rpa + 1))
                if rpa == 0:
                    while not checkIp(ip) or getGateway(ip) == False:
                        ip = input('IP is not valid or already exist, Enter RPA {} IP: '.format(rpa + 1))
                    gateway = getGateway(ip)
                else:
                    while not checkIp(ip) or getGateway(ip) != gateway:
                        ip = input('IP is not valid or already exist, Enter RPA {} IP: '.format(rpa + 1))
                rpaIpList.append(ip)
            print()
            print('Storage:')
            for datastore in range(0, len(clusterDictDS[clusterSelected])):
                print('[{}] {}'.format(datastore + 1, clusterDictDS[clusterSelected][datastore]))
            try:
                dsSelected = int(input('Select a destination storage for RPA {}: '.format(rpa + 1)))
            except:
                ValueError
            while dsSelected < 1 or dsSelected > datastore + 1:
                try:
                    dsSelected = int(input('Your selection is not from the list, Please select again: '))
                except:
                    IndexError
            ds.append(clusterDictDS[clusterSelected][dsSelected - 1])
            dsSelected = 0
        print()
        if deployType ==1:
            path = mobOVA[clusterSelected - 1]
            net = "RecoverPoint Management Network"
            os.path.join('C:', '\\', 'Program Files', 'VMware', 'VMware OVF Tool')
            os.chdir('C:\\Program Files\\VMware\\VMware OVF Tool')
            ova = '5.0(d.205).ova'
            cluster_name = input("insert cluster name:\n")
            command_list = []
            data_list = []
            file_name = "%s.csv" % cluster_name
            path = mobOVA[clusterSelected - 1]
            net = "RecoverPoint Management Network"
            os.path.join('C:', '\\', 'Program Files', 'VMware', 'VMware OVF Tool')
            os.chdir('C:\\Program Files\\VMware\\VMware OVF Tool')
            ova = '5.0(d.205).ova'
            command_list = []
            data_list = []
            file_name = "%s.csv" % cluster_name
            while rpaLength < len(rpaIpList):
                try:
                    for esxLength in range(0, len(clusterDictESX[clusterSelected])):
                        # print('{} : {}'.format(rpaIpList[rpaLength], clusterDictESX[clusterSelected][esxLength]))
                        path2 = "vi://administrator@vsphere.local:Kashya123!@%s/%s" % (
                            vcIp, path + '/' + clusterDictESX[clusterSelected][esxLength])
                        # print (path)
                        command = Deploy_RPAs(rpaNameList[rpaLength], ds[rpaLength], net,
                                              clusterDictVlan[clusterSelected][vlanSelected - 1], rpaIpList[rpaLength],
                                              netmask, gateway, ova.strip(), path2)
                        print(command)
                        p = subprocess.Popen(command, stdin=PIPE, stdout=sys.stdout, stderr=PIPE, shell=True)
                        print(p)
                        data = {
                            'RPAName': rpaNameList[rpaLength],
                            'DataStore': ds[rpaLength],
                            'Network': net,
                            'LAN_VLAN': clusterDictVlan[clusterSelected][vlanSelected - 1],
                            'RPAIP': rpaIpList[rpaLength],
                            'netmask': netmask,
                            'gateway': gateway,
                            'OVA': ova.strip(),
                            'path': path2,
                            'vcIP': vcIp
                        }
                        data_list.append(data)
                        rpaLength += 1
                    p.wait()
                except:
                    print("Deploy was failed to start")
                    IndexError
            print("create ENV file....")
            path = r"C:\Users\nahmia\PycharmProjects\untitled"
            os.chdir(path)
            with open(file_name, 'w') as csvfile:
                fieldnames = ['RPAName', 'RPAnum', 'DataStore', 'Network', 'LAN_VLAN', 'RPAIP', 'netmask', 'gateway', 'OVA',
                          'path', 'Cluster name', 'mgmt_ip', 'KVOL', 'WAN_VLAN','iSCSI1_VLAN','iSCSI2_VLAN', 'TOPOLOGY', 'IPWAN_RPA1', 'IPWAN_RPA2',
                          'IPDATA1_RPA1', 'IPDATA2_RPA1', 'IPDATA1_RPA2', 'IPDATA2_RPA2', 'vcUser', 'vcPassword','vcIP']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for data in data_list:
                    writer.writerow(data)

            print(time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()))
            if p.returncode == 0:
                print("Script will enable SSH soon....\n ")
                for remaining in range(400, -1, -1):
                    sys.stdout.write("\r")
                    sys.stdout.write("{:2d} seconds remaining.".format(remaining))
                    sys.stdout.flush()
                    time.sleep(1)

            vmlist = content.rootFolder.childEntity[0].vmFolder.childEntity
            for vm in vmlist:
                if vm.name in rpaNameList:
                    enableRemoteConnection(vm, si)
            sys.exit(1)





    # ======================= Deploy OVA: Import from file =======================

    if deployFile == 2:
        print('File path:')
        while file_path == '':
            root = tk.Tk()
            root.withdraw()
            file_path = filedialog.askopenfilename()
        print(file_path + '\n')
        file_name = file_path
        #path = r"C:\Users\nahmia\PycharmProjects\untitled"
        command_list = []
        LAN_RPAs_list = []
        with open(file_name, "r") as file:
            reader = csv.DictReader(file, delimiter=",")
            for row in reader:
                LAN_RPAs_list.append(row["RPAIP"])
                ipWAN_rpa1 = row["IPWAN_RPA1"]
                ipWAN_rpa2 = row["IPWAN_RPA2"]
                ipDATA1_rpa1 = row["IPDATA1_RPA1"]
                ipDATA2_rpa1 = row["IPDATA2_RPA1"]
                ipDATA1_rpa2 = row["IPDATA1_RPA2"]
                ipDATA2_rpa2 = row["IPDATA2_RPA2"]
                cluster_name = row["Cluster name"]
                if row["gateway"] not in (None, ""):
                    gateway = row["gateway"]
                if row["vcIP"] not in (None, ""):
                    vcIp = row["vcIP"]
                mgmt_ip = row["mgmt_ip"]
                Topology = row["TOPOLOGY"]
                WANvlanSelected = row["WAN_VLAN"]
                DATA1vlanSelected = row["iSCSI1_VLAN"]
                DATA2vlanSelected = row["iSCSI2_VLAN"]
                kvolDS = row["KVOL"]
                command = Deploy_RPAs(row['RPAName'], row['DataStore'], row['Network'], row['LAN_VLAN'], row['RPAIP'],
                                      row['netmask'], row['gateway'], row['OVA'], row['path'])
                command_list.append(command)
                #print(command)
            for i in LAN_RPAs_list:
                if i == "" or i == " " or i is None:
                    LAN_RPAs_list.remove(i)
        default_context = ssl._create_default_https_context
        ssl._create_default_https_context = ssl._create_unverified_context
        inputs = {'vcenter_password': 'Kashya123!', 'vcenter_user': r"administrator@vsphere.local"}
        si = SmartConnect(host=vcIp, user=inputs['vcenter_user'], pwd=inputs['vcenter_password'])
        content = si.RetrieveContent()

        ova = selectBuild(build)
        os.path.join('C:', '\\', 'Program Files', 'VMware', 'VMware OVF Tool')
        os.chdir('C:\\Program Files\\VMware\\VMware OVF Tool')
        ova = '5.0(d.205).ova'
        for command in command_list:
            p = subprocess.Popen(command, stdin=PIPE, stdout=sys.stdout, stderr=PIPE, shell=True)
        p.wait()
        print("start wait 400 sec Until the deploy will done..")
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()))
        print("Script will enable SSH soon....\n ")
        for remaining in range(400, -1, -1):
            sys.stdout.write("\r")
            sys.stdout.write("{:2d} seconds remaining.".format(remaining))
            sys.stdout.flush()
            time.sleep(1)

        vmlist = content.rootFolder.childEntity[0].vmFolder.childEntity
        for vm in vmlist:
            if vm.name in rpaNameList:
                enableRemoteConnection(vm, si)
        print()



#==============#
#     DGUI     #
#==============#

if deployType == 2 or deployType == 3:# DGUI
    if deployType ==2:
        print('Deploy OVA:\n[1] Manual\n[2] Import from file')
        try:
            deployFile = int(input('Please select how to deploy OVA (1-2): '))
        except:
            ValueError
        while deployFile not in range(1, 3):
            try:
                deployFile = int(input('Your selection is not from the list, Please select again: '))
            except:
                ValueError
        print('\n---------------------------------------------------\n')
    if deployFile == 1:
        if deployType ==2:
            vcIp = input('Please insert vCenter IP: ')  # get VC and check the connection
            while not checkIp(vcIp):
                vcIp = input('vCenter IP is not valid, please insert vCenter IP: ')
        #connectVC(vcIp)
        cluster_name = input("insert cluster name:\n")
        LAN_RPAs_list = []
        if deployType == 2:
            RPA1 = input("Insert RPA1 LAN IP: \n")
            while not checkIp(RPA1):
                RPA1 = input("Invalid,Insert RPA1 LAN IP: \n")
            RPA2 = input("Insert RPA2 LAN IP: \n")
            while not checkIp(RPA2):
                RPA2 = input("Invalid,Insert RPA2 LAN IP: \n")
            LAN_RPAs_list.append(RPA1)
            LAN_RPAs_list.append(RPA2)
            gateway = input("Insert LAN Gateway: \n")
            while not checkIp(gateway):
                gateway = input("Invalid,Insert LAN Gateway: \n")

        mgmt_ip = input("Insert IP for mgmt cluster: \n")
        while not checkIp(mgmt_ip):
            mgmt_ip = input("Invalid IP,Please try again to Insert IP for mgmt cluster: \n")
        if deployType == 2:
            print('\nClusters list:')  # Choose a cluster and get ESXs under it via mobOVA
            default_context = ssl._create_default_https_context
            ssl._create_default_https_context = ssl._create_unverified_context
            inputs = {'vcenter_password': 'Kashya123!', 'vcenter_user': r"administrator@vsphere.local"}
            si = SmartConnect(host=vcIp, user=inputs['vcenter_user'], pwd=inputs['vcenter_password'])
            content = si.RetrieveContent()
            for dataCenter in range(0, len(content.rootFolder.childEntity)):  # Cluster
                for cluster in range(0, len(content.rootFolder.childEntity[dataCenter].hostFolder.childEntity)):
                    if 'domain' not in str(content.rootFolder.childEntity[dataCenter].hostFolder.childEntity[cluster]):
                        for folder in range(0, len(
                                content.rootFolder.childEntity[dataCenter].hostFolder.childEntity[cluster].childEntity)):
                            for host in range(0, len(
                                    content.rootFolder.childEntity[dataCenter].hostFolder.childEntity[cluster].childEntity[
                                        folder].host)):
                                esx.append(
                                    content.rootFolder.childEntity[dataCenter].hostFolder.childEntity[cluster].childEntity[
                                        folder].host[host].name)
                                # esx.append(socket.gethostbyname(content.rootFolder.childEntity[dataCenter].hostFolder.childEntity[cluster].childEntity[folder].host[host].name))
                            if esx != []:
                                for datastore in range(0, len(
                                        content.rootFolder.childEntity[dataCenter].hostFolder.childEntity[
                                            cluster].childEntity[folder].datastore)):
                                    if content.rootFolder.childEntity[dataCenter].hostFolder.childEntity[
                                        cluster].childEntity[folder].datastore[
                                        datastore].summary.multipleHostAccess == True:
                                        ds.append(content.rootFolder.childEntity[dataCenter].hostFolder.childEntity[
                                                      cluster].childEntity[folder].datastore[datastore].name)
                                for network in range(0, len(
                                        content.rootFolder.childEntity[dataCenter].hostFolder.childEntity[
                                            cluster].childEntity[folder].network)):
                                    vlan.append(content.rootFolder.childEntity[dataCenter].hostFolder.childEntity[
                                                    cluster].childEntity[folder].network[network].name)
                                print('[{}] {}'.format(clusterNum,
                                                       content.rootFolder.childEntity[dataCenter].hostFolder.childEntity[
                                                           cluster].childEntity[folder].name))
                                mobOVA.append('{}/{}/{}/{}'.format(content.rootFolder.childEntity[dataCenter].name,
                                                                   content.rootFolder.childEntity[
                                                                       dataCenter].hostFolder.name,
                                                                   content.rootFolder.childEntity[
                                                                       dataCenter].hostFolder.childEntity[cluster].name,
                                                                   content.rootFolder.childEntity[
                                                                       dataCenter].hostFolder.childEntity[
                                                                       cluster].childEntity[folder].name))
                                mobLocation.append(
                                    'content.rootFolder.childEntity[{}].hostFolder.childEntity[{}].childEntity[{}]'.format(
                                        dataCenter, cluster, folder))
                                clusterDictESX.update({clusterNum: esx})
                                clusterDictDS.update({clusterNum: ds})
                                clusterDictVlan.update({clusterNum: vlan})
                                esx = []
                                ds = []
                                vlan = []
                                clusterNum += 1
                    else:
                        for host in range(0, len(
                                content.rootFolder.childEntity[dataCenter].hostFolder.childEntity[cluster].host)):
                            esx.append(
                                content.rootFolder.childEntity[dataCenter].hostFolder.childEntity[cluster].host[host].name)
                            # esx.append(socket.gethostbyname(content.rootFolder.childEntity[dataCenter].hostFolder.childEntity[cluster].childEntity[folder].host[host].name))
                        if esx != []:
                            for datastore in range(0, len(
                                    content.rootFolder.childEntity[dataCenter].hostFolder.childEntity[cluster].datastore)):
                                if content.rootFolder.childEntity[dataCenter].hostFolder.childEntity[cluster].datastore[
                                    datastore].summary.multipleHostAccess == True:
                                    ds.append(content.rootFolder.childEntity[dataCenter].hostFolder.childEntity[
                                                  cluster].datastore[datastore].name)
                            for network in range(0, len(
                                    content.rootFolder.childEntity[dataCenter].hostFolder.childEntity[cluster].network)):
                                vlan.append(
                                    content.rootFolder.childEntity[dataCenter].hostFolder.childEntity[cluster].network[
                                        network].name)
                            print('[{}] {}'.format(clusterNum,
                                                   content.rootFolder.childEntity[dataCenter].hostFolder.childEntity[
                                                       cluster].name))
                            mobOVA.append('{}/{}/{}'.format(content.rootFolder.childEntity[dataCenter].name,
                                                            content.rootFolder.childEntity[dataCenter].hostFolder.name,
                                                            content.rootFolder.childEntity[
                                                                dataCenter].hostFolder.childEntity[cluster].name))
                            mobLocation.append(
                                'content.rootFolder.childEntity[{}].hostFolder.childEntity[{}]'.format(dataCenter, cluster))
                            clusterDictESX.update({clusterNum: esx})
                            clusterDictDS.update({clusterNum: ds})
                            clusterDictVlan.update({clusterNum: vlan})
            try:
                clusterSelected = int(input('Enter the cluster number for deploy OVA: '))
            except:
                ValueError
        print('Choose KVOL Storage:')
        for datastore in range(0, len(clusterDictDS[clusterSelected])):
            print('[{}] {}'.format(datastore + 1, clusterDictDS[clusterSelected][datastore]))
        kdsSelected = int(input('Select a destination storage for KVOL :'))
        while kdsSelected < 1 or kdsSelected > datastore + 1:
            try:
                kdsSelected = int(input('Your selection is not from the list, Please select again: '))
            except:
                IndexError
        kvolDS = clusterDictDS[clusterSelected][kdsSelected - 1]

        print("Network Adapters Configuration\n")
        print("Choose your Topology:\n")

        print("(1)" + 'WAN and LAN on separate network adapters + Data (iSCSI) on same network adapter as LAN')
        print(
            "(2)" + 'WAN and LAN on separate network adapters + Data (iSCSI) on separate network adapter from WAN and LAN')
        print("(3)" + 'WAN and LAN on separate network adapters + Data (iSCSI) on 2 dedicated network adapters')
        print("(4)" + 'WAN and LAN on same network adapter + Data (iSCSI) on same network adapter as WAN and LAN')
        print("(5)" + 'WAN and LAN on same network adapter + Data (iSCSI) on separate network adapter from WAN and LAN')

        WANvlanSelected = ""
        DATA1vlanSelected = ""
        DATA2vlanSelected = ""
        ipWAN_rpa1 = ""
        ipWAN_rpa2 = ""
        ipDATA_rpa1 = ""
        ipDATA_rpa2 = ""
        ipDATA1_rpa1 = ""
        ipDATA1_rpa2 = ""
        ipDATA2_rpa1 = ""
        ipDATA2_rpa2 = ""

        Topology = input("Insert your topology number:\n")
        while (Topology != "1" and Topology != "2" and Topology != "3" and Topology != "4" and Topology != "5"):
            print("Invalid number,please try again!!!")
            Topology = input("Insert your topology number:\n")

        if Topology == "1":
            print('Network Mapping:')  # vlan selection choosing by spec
            for network in range(0, len(clusterDictVlan[clusterSelected])):
                print('[{}] {}'.format(network + 1, clusterDictVlan[clusterSelected][network]))
            WANvlanSelected = int(input('Enter the WAN network: '))
            while WANvlanSelected < 1 or WANvlanSelected > network + 1:
                try:
                    WANvlanSelected = int(input('Your selection is not from the list, Please select again: '))
                except:
                    IndexError
            WANvlanSelected = clusterDictVlan[clusterSelected][WANvlanSelected - 1]

            ipWAN_rpa1 = input('Enter RPA1 WAN IP: ')
            while not checkIp(ipWAN_rpa1):
                ipWAN_rpa1 = input('Invalid IP,Enter RPA1 WAN IP: ')
            ipWAN_rpa2 = input('Enter RPA2  WAN IP: ')
            while not checkIp(ipWAN_rpa2):
                ipWAN_rpa2 = input('Invalid IP,Enter RPA2  WAN IP: ')
        elif Topology == "2":
            print('Network Mapping:')  # vlan selection choosing by spec
            for network in range(0, len(clusterDictVlan[clusterSelected])):
                print('[{}] {}'.format(network + 1, clusterDictVlan[clusterSelected][network]))
            WANvlanSelected = int(input('Enter the WAN network: '))
            while WANvlanSelected < 1 or WANvlanSelected > network + 1:
                try:
                    WANvlanSelected = int(input('Your selection is not from the list, Please select again: '))
                except:
                    IndexError
            WANvlanSelected = clusterDictVlan[clusterSelected][WANvlanSelected - 1]

            print('Network Mapping:')  # vlan selection choosing by spec
            for network in range(0, len(clusterDictVlan[clusterSelected])):
                print('[{}] {}'.format(network + 1, clusterDictVlan[clusterSelected][network]))
            DATA1vlanSelected = int(input('Enter the iSCSI1  network: '))
            while DATA1vlanSelected < 1 or DATA1vlanSelected > network + 1:
                try:
                    DATA1vlanSelected = int(input('Your selection is not from the list, Please select again: '))
                except:
                    IndexError
            DATA1vlanSelected = clusterDictVlan[clusterSelected][DATA1vlanSelected - 1]
            ipWAN_rpa1 = input('Enter RPA1  WAN IP:')
            while not checkIp(ipWAN_rpa1):
                ipWAN_rpa1 = input('Invalid IP,Enter RPA1  WAN IP:')
            ipWAN_rpa2 = input('Enter RPA2  WAN IP:')
            while not checkIp(ipWAN_rpa2):
                ipWAN_rpa2 = input('Invalid IP,Enter RPA2  WAN IP:')
            ipDATA1_rpa1 = input('Enter RPA1 DATA IP: ')
            while not checkIp(ipDATA1_rpa1):
                ipDATA1_rpa1 = input('Invalid IP,Enter RPA1  DATA IP:')
            ipDATA1_rpa2 = input('Enter RPA2 DATA IP: ')
            while not checkIp(ipDATA1_rpa2):
                ipDATA1_rpa2 = input('Invalid IP,Enter RPA2 DATA IP:')
        elif Topology == "3":
            print('Network Mapping:')  # vlan selection choosing by spec
            for network in range(0, len(clusterDictVlan[clusterSelected])):
                print('[{}] {}'.format(network + 1, clusterDictVlan[clusterSelected][network]))
            WANvlanSelected = int(input('Enter the WAN network: '))
            while WANvlanSelected < 1 or WANvlanSelected > network + 1:
                try:
                    WANvlanSelected = int(input('Your selection is not from the list, Please select again: '))
                except:
                    IndexError
            WANvlanSelected = clusterDictVlan[clusterSelected][WANvlanSelected - 1]
            network = 0

            print('Network Mapping:')  # vlan selection choosing by spec
            for network in range(0, len(clusterDictVlan[clusterSelected])):
                print('[{}] {}'.format(network + 1, clusterDictVlan[clusterSelected][network]))
            DATA1vlanSelected = int(input('Enter the iSCSI1  network: '))
            while DATA1vlanSelected < 1 or DATA1vlanSelected > network + 1:
                try:
                    DATA1vlanSelected = int(input('Your selection is not from the list, Please select again: '))
                except:
                    IndexError
            DATA1vlanSelected = clusterDictVlan[clusterSelected][DATA1vlanSelected - 1]
            network = 0
            print('Network Mapping:')  # vlan selection choosing by spec
            for network in range(0, len(clusterDictVlan[clusterSelected])):
                print('[{}] {}'.format(network + 1, clusterDictVlan[clusterSelected][network]))
            DATA2vlanSelected = int(input('Enter the iSCSI2  network: '))
            while DATA2vlanSelected < 1 or DATA2vlanSelected > network + 1:
                try:
                    DATA2vlanSelected = int(input('Your selection is not from the list, Please select again: '))
                except:
                    IndexError
            DATA2vlanSelected = clusterDictVlan[clusterSelected][DATA2vlanSelected - 1]
            ipWAN_rpa1 = input('Enter RPA1 WAN IP: ')
            while not checkIp(ipWAN_rpa1):
                ipWAN_rpa1 = input('Invalid IP,Enter RPA1  WAN IP:')
            ipWAN_rpa2 = input('Enter RPA2 WAN IP: ')
            while not checkIp(ipWAN_rpa2):
                ipWAN_rpa2 = input('Invalid IP,Enter RPA2  WAN IP:')
            ipDATA1_rpa1 = input('Enter RPA1 DATA1 IP:')
            while not checkIp(ipDATA1_rpa1):
                ipDATA1_rpa1 = input('Invalid IP,Enter RPA1  DATA1 IP:')
            ipDATA2_rpa1 = input('Enter RPA1 DATA2 IP:')
            while not checkIp(ipDATA2_rpa1):
                ipDATA2_rpa1 = input('Invalid IP,Enter RPA1  DATA2 IP:')
            ipDATA1_rpa2 = input('Enter RPA2 DATA1 IP:')
            while not checkIp(ipDATA1_rpa2):
                ipDATA1_rpa2 = input('Invalid IP,Enter RPA2  DATA1 IP:')
            ipDATA2_rpa2 = input('Enter RPA2 DATA2 IP:')
            while not checkIp(ipDATA2_rpa2):
                ipDATA2_rpa2 = input('Invalid IP,Enter RPA2  DATA2 IP:')

        elif Topology == "5":
            print('Network Mapping:')  # vlan selection choosing by spec
            for network in range(0, len(clusterDictVlan[clusterSelected])):
                print('[{}] {}'.format(network + 1, clusterDictVlan[clusterSelected][network]))
            DATA1vlanSelected = int(input('Enter the iSCSI1  network: '))
            while DATA1vlanSelected < 1 or DATA1vlanSelected > network + 1:
                try:
                    DATA1vlanSelected = int(input('Your selection is not from the list, Please select again: '))
                except:
                    IndexError
            DATA1vlanSelected = clusterDictVlan[clusterSelected][DATA1vlanSelected - 1]
            ipDATA1_rpa1 = input('Enter  RPA1 DATA IP: ')
            while not checkIp(ipDATA1_rpa1):
                ipDATA1_rpa1 = input('Invalid IP,Enter  RPA1 DATA IP:')
            ipDATA1_rpa2 = input('Enter  RPA2 DATA IP: ')
            while not checkIp(ipDATA1_rpa2):
                ipDATA1_rpa2 = input('Invalid IP,Enter  RPA2 DATA IP:')
        if deployType == 3:
            path = mobOVA[clusterSelected - 1]
            net = "RecoverPoint Management Network"
            os.path.join('C:', '\\', 'Program Files', 'VMware', 'VMware OVF Tool')
            os.chdir('C:\\Program Files\\VMware\\VMware OVF Tool')
            ova = '5.0(d.205).ova'
            command_list = []
            data_list = []
            file_name = "%s.csv" % cluster_name
            while rpaLength < len(rpaIpList):
                try:
                    for esxLength in range(0, len(clusterDictESX[clusterSelected])):
                        # print('{} : {}'.format(rpaIpList[rpaLength], clusterDictESX[clusterSelected][esxLength]))
                        path2 = "vi://administrator@vsphere.local:Kashya123!@%s/%s" % (
                            vcIp, path + '/' + clusterDictESX[clusterSelected][esxLength])
                        # print (path)
                        command = Deploy_RPAs(rpaNameList[rpaLength], ds[rpaLength], net,
                                              clusterDictVlan[clusterSelected][vlanSelected - 1], rpaIpList[rpaLength],
                                              netmask, gateway, ova.strip(), path2)
                        print(command)
                        p = subprocess.Popen(command, stdin=PIPE, stdout=sys.stdout, stderr=PIPE, shell=True)
                        print(p)
                        data = {
                            'RPAName': rpaNameList[rpaLength],
                            'DataStore': ds[rpaLength],
                            'Network': net,
                            'LAN_VLAN': clusterDictVlan[clusterSelected][vlanSelected - 1],
                            'RPAIP': rpaIpList[rpaLength],
                            'netmask': netmask,
                            'gateway': gateway,
                            'OVA': ova.strip(),
                            'path': path2,
                            'vcIP':vcIp
                        }
                        data_list.append(data)
                        rpaLength += 1
                except:
                    IndexError
        file_name = "%s.csv" % cluster_name
        path = r"C:\Users\nahmia\PycharmProjects\untitled"
        os.chdir(path)
        data2 = {
            'Cluster name': cluster_name,
            'mgmt_ip': mgmt_ip,
            'KVOL': kvolDS,
            'WAN_VLAN': WANvlanSelected,
            'iSCSI1_VLAN': DATA1vlanSelected,
            'iSCSI2_VLAN': DATA2vlanSelected,
            'TOPOLOGY': Topology,
            'IPWAN_RPA1': ipWAN_rpa1,
            'IPWAN_RPA2': ipWAN_rpa2,
            'IPDATA1_RPA1': ipDATA1_rpa1,
            'IPDATA2_RPA1': ipDATA2_rpa1,
            'IPDATA1_RPA2': ipDATA1_rpa2,
            'IPDATA2_RPA2': ipDATA2_rpa2,
            'vcUser': "administrator@vsphere.local",
            'vcPassword': "Kashya123!",
            'gateway': gateway,
            'vcIP':vcIp

        }

        if os.path.exists(path+file_name):
            with open(file_name, 'a') as csvfile:
                writer = csv.DictWriter(csvfile)
                writer.writeheader()
                if deployType == 3:
                    for data in data_list:
                        writer.writerow(data)
                writer.writerow(data2)
        else:
            with open(file_name, 'w') as csvfile:
                fieldnames = ['RPAName', 'RPAnum', 'DataStore', 'Network', 'LAN_VLAN', 'RPAIP', 'netmask', 'gateway', 'OVA',
                              'path', 'Cluster name', 'mgmt_ip', 'KVOL', 'WAN_VLAN','iSCSI1_VLAN','iSCSI2_VLAN', 'TOPOLOGY', 'IPWAN_RPA1', 'IPWAN_RPA2',
                              'IPDATA1_RPA1', 'IPDATA2_RPA1', 'IPDATA1_RPA2', 'IPDATA2_RPA2', 'vcUser', 'vcPassword','vcIP']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for IP in LAN_RPAs_list:
                    data3 = {'RPAIP':IP}
                    writer.writerow(data3)
                if deployType ==3:
                    for data in data_list:
                        writer.writerow(data)
                writer.writerow(data2)

        p.wait()
        print("start wait 400 sec Until the deploy will done..")
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()))
        print("Script will enable SSH soon....\n ")
        for remaining in range(400, -1, -1):
            sys.stdout.write("\r")
            sys.stdout.write("{:2d} seconds remaining.".format(remaining))
            sys.stdout.flush()
            time.sleep(1)

        default_context = ssl._create_default_https_context
        ssl._create_default_https_context = ssl._create_unverified_context
        inputs = {'vcenter_password': 'Kashya123!', 'vcenter_user': r"administrator@vsphere.local"}
        si = SmartConnect(host=vcIp, user=inputs['vcenter_user'], pwd=inputs['vcenter_password'])
        content = si.RetrieveContent()
        vmlist = content.rootFolder.childEntity[0].vmFolder.childEntity
        for vm in vmlist:
            if vm.name in rpaNameList:
                enableRemoteConnection(vm, si)
        print()

    if deployFile ==2:
        if deployType ==2:
            print('---------------------------------------------------\n')
            print('File path:')
            while file_path == '':
                root = tk.Tk()
                root.withdraw()
                file_path = filedialog.askopenfilename()
        print(file_path + '\n')
        file_name = file_path
        # path = r"C:\Users\nahmia\PycharmProjects\untitled"
        command_list = []
        LAN_RPAs_list = []
        with open(file_name, "r") as file:
            reader = csv.DictReader(file, delimiter=",")
            for row in reader:
                LAN_RPAs_list.append(row["RPAIP"])
                ipWAN_rpa1 = row["IPWAN_RPA1"]
                ipWAN_rpa2 = row["IPWAN_RPA2"]
                ipDATA1_rpa1 = row["IPDATA1_RPA1"]
                ipDATA2_rpa1 = row["IPDATA2_RPA1"]
                ipDATA1_rpa2 = row["IPDATA1_RPA2"]
                ipDATA2_rpa2 = row["IPDATA2_RPA2"]
                cluster_name = row["Cluster name"]
                if row["gateway"] not in (None, ""):
                    gateway = row["gateway"]
                if row["vcIP"] not in (None, ""):
                    vcIp = row["vcIP"]
                mgmt_ip = row["mgmt_ip"]
                Topology = row["TOPOLOGY"]
                WANvlanSelected = row["WAN_VLAN"]
                DATA1vlanSelected = row["iSCSI1_VLAN"]
                DATA2vlanSelected = row["iSCSI2_VLAN"]
                kvolDS = row["KVOL"]
                command = Deploy_RPAs(row['RPAName'], row['DataStore'], row['Network'], row['LAN_VLAN'], row['RPAIP'],
                                      row['netmask'], row['gateway'], row['OVA'], row['path'])
        for i in LAN_RPAs_list:
            if i == "" or i == " " or i is None:
                LAN_RPAs_list.remove(i)
        if deployType == 2:
            print("Verify SSH is Enabled...")
            default_context = ssl._create_default_https_context
            ssl._create_default_https_context = ssl._create_unverified_context
            inputs = {'vcenter_password': 'Kashya123!', 'vcenter_user': r"administrator@vsphere.local"}
            si = SmartConnect(host=vcIp, user=inputs['vcenter_user'], pwd=inputs['vcenter_password'])
            content = si.RetrieveContent()
            vmlist = content.rootFolder.childEntity[0].vmFolder.childEntity
            for vm in vmlist:
                if vm.name in rpaNameList:
                    enableRemoteConnection(vm, si)
            print("SSH Enabled!!")


    class PythonTest(unittest.TestCase):
        # RPA1 = input("Insert RPA IP:\n")
        print("Open DGUI....")
        if deployFile == 1:
            RPA1 = rpaIpList[0]
            RPA2 = rpaIpList[1]
        else:
            RPA1 = LAN_RPAs_list[0]
            RPA2 = LAN_RPAs_list[1]
        Cluster_name = cluster_name
        mgmt_IP = mgmt_ip
        DG = gateway
        VC = vcIp
        ds_kvol = kvolDS
        vcUser = "administrator@vsphere.local"
        vcPassword = "Kashya123!"
        if Topology == "1":
            WAN_RPA1 = ipWAN_rpa1
            WAN_RPA2 = ipWAN_rpa2
            WAN_Vlan = WANvlanSelected
        if Topology == "2":
            WAN_Vlan = WANvlanSelected
            ISCSI_A = DATA1vlanSelected
            WAN_RPA1 = ipWAN_rpa1
            WAN_RPA2 = ipWAN_rpa2
            Data1_RPA1 = ipDATA1_rpa1
            Data1_RPA2 = ipDATA1_rpa2
        if Topology == "3":
            WAN_RPA1 = ipWAN_rpa1
            WAN_RPA2 = ipWAN_rpa2
            Data1_RPA1 = ipDATA1_rpa1
            Data2_RPA1 = ipDATA2_rpa1
            Data1_RPA2 = ipDATA1_rpa2
            Data2_RPA2 = ipDATA2_rpa2
            ISCSI_A = DATA1vlanSelected
            ISCSI_B = DATA2vlanSelected
            WAN_Vlan = WANvlanSelected
        if Topology == "5":
            ISCSI_A = DATA1vlanSelected
            Data1_RPA1 = ipDATA1_rpa1
            Data1_RPA2 = ipDATA1_rpa2

        # print(WAN_Vlan,ISCSI_A,ISCSI_B)


        def setUp(self):
            chrome_options = webdriver.ChromeOptions()
            chrome_options.add_argument("--incognito")
            chromedriver = r"C:\chromedriver\chromedriver.exe"
            os.environ["webdriver.chrome.driver"] = chromedriver
            self.driver = webdriver.Chrome(chromedriver, chrome_options=chrome_options)
            self.driver.maximize_window()
            self.driver.implicitly_wait(30)
            # self.driver.get("https://10.76.10.166/WDM/#/welcome")
            # self.base_url = "https://" + (self.RPA1) + "/WDM/#/welcome"
            self.base_url = "https://" + self.RPA1 + "/WDM/#/welcome"
            self.verificationErrors = []
            self.accept_next_alert = True
            self.wait = WebDriverWait(self.driver, 10)

        def test_python(self):
            # Start Page
            driver = self.driver
            driver.get(self.base_url + "/WDM/#/welcome")
            self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button.blue-link-button")))
            time.sleep(1)
            driver.find_element_by_css_selector("button.blue-link-button").click()
            # driver.find_element_by_id("ccaOriginTrial").click()
            driver.find_element_by_css_selector("div.radio > label").click()
            self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "div.radio > label")))
            driver.find_element_by_xpath("(//button[@type='button'])[2]").click()
            # self.wait.until(EC.element_to_be_clickable((By.XPATH, "//div[@id='detailsView']/div/div/div/div/div/div/a/span")))
            time.sleep(7)
            # VC PAGE
            driver.find_element_by_name("vcIP").clear()
            driver.find_element_by_name("vcIP").send_keys(self.VC.strip())
            driver.find_element_by_name("vcUser").clear()
            driver.find_element_by_name("vcUser").send_keys(self.vcUser)
            driver.find_element_by_name("vcPass").clear()
            driver.find_element_by_name("vcPass").send_keys(self.vcPassword)
            driver.find_element_by_xpath("//div[@id='preForm']/div[2]/div/button").click()
            self.wait.until(EC.element_to_be_clickable((By.XPATH, "//div[3]/button[2]")))
            time.sleep(1)
            driver.find_element_by_xpath("//div[3]/button[2]").click()
            time.sleep(1)
            self.wait.until(EC.element_to_be_clickable((By.XPATH, "(//button[@type='button'])[2]")))
            # ERROR: Caught exception [Error: locator strategy either id or name must be specified explicitly.]
            driver.find_element_by_xpath("(//button[@type='button'])[2]").click()
            self.wait.until(EC.element_to_be_clickable((By.XPATH,
                                                        "//form[@id='envForm']/div[2]/div[2]/div/vm-selectable-list/div/div/div/div/div[2]/div/div[2]/div/div/div/div/div")))

            driver.find_element_by_name("clusterName").clear()
            driver.find_element_by_name("clusterName").send_keys(self.Cluster_name)
            Select(driver.find_element_by_xpath(
                "//form[@id='envForm']/div/div[2]/div/div[2]/select")).select_by_visible_text(
                "Authenticated and encrypted")
            driver.find_element_by_xpath("//form[@id='envForm']/div/div[2]/div/div[2]/select").click()
            driver.find_element_by_name("dnsServers").clear()
            driver.find_element_by_name("dnsServers").send_keys("10.76.8.41")
            driver.find_element_by_name("ntpServers").clear()
            driver.find_element_by_name("ntpServers").send_keys("10.254.140.21")
            driver.find_element_by_xpath(
                "//form[@id='envForm']/div[2]/div[2]/div/vm-selectable-list/div/div/div/div/div[2]/div/div[2]/div/div/div/div/div").click()
            driver.find_element_by_xpath("//form[@id='envForm']/button").click()
            time.sleep(5)
            # ERROR: Caught exception [Error: locator strategy either id or name must be specified explicitly.]
            # self.wait.until(EC.element_to_be_clickable((By.XPATH, "//div[@id='table-wrapper']/table/tbody/tr/th[@title='RPVENV4_Local_Kvol']")))
            driver.find_element_by_xpath("( // button[ @ type = 'button'])[2]").click()
            driver.find_element_by_xpath(
                "// div[ @ id = 'table-wrapper'] / table / tbody / tr / th[@title='" + self.ds_kvol + "']").click()
            time.sleep(1)
            self.wait.until(EC.element_to_be_clickable((By.XPATH, "(//button[@type='button'])[2]")))
            driver.find_element_by_xpath("(//button[@type='button'])[2]").click()
            time.sleep(3)
            if Topology == "1":
                # WAN and LAN on separate network adapters + Data (iSCSI) on same network adapter as LAN
                driver.find_element_by_name("inpClusterManagementIpv4").clear()
                driver.find_element_by_name("inpClusterManagementIpv4").send_keys(self.mgmt_IP)
                Select(driver.find_element_by_xpath(
                    "//form[@id='connectivityForm']/div[2]/div/table[2]/tbody[2]/tr/td[2]/select")).select_by_visible_text(
                    "WAN and LAN on separate network adapters")
                Select(driver.find_element_by_xpath(
                    "//form[@id='connectivityForm']/div[2]/div/table[2]/tbody[2]/tr[2]/td[2]/select")).select_by_visible_text(
                    "Data (iSCSI) on same network adapter as LAN")
                Select(driver.find_element_by_xpath(
                    "//form[@id='connectivityForm']/div[2]/div/table[2]/tbody[4]/tr/td/div/table[2]/tbody/tr/td[2]/select")).select_by_visible_text(
                    self.WAN_Vlan)

                driver.find_element_by_name("inpIpv4Netmask").clear()
                driver.find_element_by_name("inpIpv4Netmask").send_keys("255.255.254.0")
                driver.find_element_by_xpath("(//input[@name='inpIpv4Netmask'])[2]").clear()
                driver.find_element_by_xpath("(//input[@name='inpIpv4Netmask'])[2]").send_keys("255.255.255.0")
                driver.find_element_by_name("input_1").clear()
                driver.find_element_by_name("input_1").send_keys(self.DG.strip())
                driver.find_element_by_name("input_10").clear()
                driver.find_element_by_name("input_10").send_keys(self.WAN_RPA1.strip())
                driver.find_element_by_name("input_12").clear()
                driver.find_element_by_name("input_12").send_keys(self.WAN_RPA2.strip())
                time.sleep(2)
                self.wait.until(EC.element_to_be_clickable((By.XPATH, "(//button[@type='button'])[2]")))
                driver.find_element_by_xpath("(//button[@type='button'])[2]").click()
                time.sleep(1000)
                driver.find_element_by_xpath("( // button[ @ type = 'button'])[2]").click()
                time.sleep(10)
                self.driver.close()
            if Topology == "2":
                # WAN and LAN on separate network adapters + Data (iSCSI) on separate network adapter from WAN and LAN
                driver.find_element_by_name("inpClusterManagementIpv4").clear()
                driver.find_element_by_name("inpClusterManagementIpv4").send_keys(self.mgmt_IP)
                Select(driver.find_element_by_xpath(
                    "//form[@id='connectivityForm']/div[2]/div/table[2]/tbody[2]/tr/td[2]/select")).select_by_visible_text(
                    "WAN and LAN on separate network adapters")
                Select(driver.find_element_by_xpath(
                    "//form[@id='connectivityForm']/div[2]/div/table[2]/tbody[2]/tr[2]/td[2]/select")).select_by_visible_text(
                    "Data (iSCSI) on separate network adapter from WAN and LAN")
                Select(driver.find_element_by_xpath(
                    "//form[@id='connectivityForm']/div[2]/div/table[2]/tbody[4]/tr/td/div/table[2]/tbody/tr/td[2]/select")).select_by_visible_text(
                    self.WAN_Vlan)
                Select(driver.find_element_by_xpath(
                    "//form[@id='connectivityForm']/div[2]/div/table[2]/tbody[4]/tr/td/div/table[3]/tbody/tr/td[2]/select")).select_by_visible_text(
                    self.ISCSI_A)

                driver.find_element_by_name("inpIpv4Netmask").clear()
                driver.find_element_by_name("inpIpv4Netmask").send_keys("255.255.254.0")
                driver.find_element_by_xpath("(//input[@name='inpIpv4Netmask'])[2]").clear()
                driver.find_element_by_xpath("(//input[@name='inpIpv4Netmask'])[2]").send_keys("255.255.255.0")
                driver.find_element_by_xpath("(//input[@name='inpIpv4Netmask'])[3]").clear()
                driver.find_element_by_xpath("(//input[@name='inpIpv4Netmask'])[3]").send_keys("255.255.252.0")
                driver.find_element_by_name("input_1").clear()
                driver.find_element_by_name("input_1").send_keys(self.DG.strip())
                driver.find_element_by_name("input_13").clear()
                driver.find_element_by_name("input_13").send_keys(self.WAN_RPA1.strip())
                driver.find_element_by_name("input_14").clear()
                driver.find_element_by_name("input_14").send_keys(self.Data1_RPA1.strip())
                driver.find_element_by_name("input_16").clear()
                driver.find_element_by_name("input_16").send_keys(self.WAN_RPA2.strip())
                driver.find_element_by_name("input_17").clear()
                driver.find_element_by_name("input_17").send_keys(self.Data1_RPA2.strip())
                time.sleep(2)
                self.wait.until(EC.element_to_be_clickable((By.XPATH, "(//button[@type='button'])[2]")))
                driver.find_element_by_xpath("(//button[@type='button'])[2]").click()
                time.sleep(1000)
                driver.find_element_by_xpath("( // button[ @ type = 'button'])[2]").click()
                time.sleep(10)
                self.driver.close()
            if Topology == "3":
                driver = self.driver
                # WAN and LAN on separate network adapters + Data (iSCSI) on 2 dedicated network adapters
                driver.find_element_by_name("inpClusterManagementIpv4").clear()
                driver.find_element_by_name("inpClusterManagementIpv4").send_keys(self.mgmt_IP)
                Select(driver.find_element_by_xpath(
                    "//form[@id='connectivityForm']/div[2]/div/table[2]/tbody[2]/tr/td[2]/select")).select_by_visible_text(
                    "WAN and LAN on separate network adapters")
                Select(driver.find_element_by_xpath(
                    "//form[@id='connectivityForm']/div[2]/div/table[2]/tbody[2]/tr[2]/td[2]/select")).select_by_visible_text(
                    "Data (iSCSI) on 2 dedicated network adapters")
                Select(driver.find_element_by_xpath(
                    "//form[@id='connectivityForm']/div[2]/div/table[2]/tbody[4]/tr/td/div/table[2]/tbody/tr/td[2]/select")).select_by_visible_text(
                    self.WAN_Vlan)
                Select(driver.find_element_by_xpath(
                    "//form[@id='connectivityForm']/div[2]/div/table[2]/tbody[4]/tr/td/div/table[3]/tbody/tr/td[2]/select")).select_by_visible_text(
                    self.ISCSI_A)
                Select(driver.find_element_by_xpath(
                    "//form[@id='connectivityForm']/div[2]/div/table[2]/tbody[4]/tr/td/div/table[4]/tbody/tr/td[2]/select")).select_by_visible_text(
                    self.ISCSI_B)

                driver.find_element_by_name("inpIpv4Netmask").clear()
                driver.find_element_by_name("inpIpv4Netmask").send_keys("255.255.254.0")
                driver.find_element_by_xpath("(//input[@name='inpIpv4Netmask'])[2]").clear()
                driver.find_element_by_xpath("(//input[@name='inpIpv4Netmask'])[2]").send_keys("255.255.255.0")
                driver.find_element_by_xpath("(//input[@name='inpIpv4Netmask'])[3]").clear()
                driver.find_element_by_xpath("(//input[@name='inpIpv4Netmask'])[3]").send_keys("255.255.252.0")
                driver.find_element_by_xpath("(//input[@name='inpIpv4Netmask'])[4]").clear()
                driver.find_element_by_xpath("(//input[@name='inpIpv4Netmask'])[4]").send_keys("255.255.252.0")
                driver.find_element_by_name("input_1").clear()
                driver.find_element_by_name("input_1").send_keys(self.DG.strip())
                driver.find_element_by_name("input_16").clear()
                driver.find_element_by_name("input_16").send_keys(self.WAN_RPA1.strip())
                driver.find_element_by_name("input_17").clear()
                driver.find_element_by_name("input_17").send_keys(self.Data1_RPA1.strip())
                driver.find_element_by_name("input_18").clear()
                driver.find_element_by_name("input_18").send_keys(self.Data2_RPA1.strip())
                driver.find_element_by_name("input_20").clear()
                driver.find_element_by_name("input_20").send_keys(self.WAN_RPA2.strip())
                driver.find_element_by_name("input_21").clear()
                driver.find_element_by_name("input_21").send_keys(self.Data1_RPA2.strip())
                driver.find_element_by_name("input_22").clear()
                driver.find_element_by_name("input_22").send_keys(self.Data2_RPA2.strip())
                time.sleep(2)
                self.wait.until(EC.element_to_be_clickable((By.XPATH, "(//button[@type='button'])[2]")))
                driver.find_element_by_xpath("(//button[@type='button'])[2]").click()
                time.sleep(1000)
                driver.find_element_by_xpath("( // button[ @ type = 'button'])[2]").click()
                time.sleep(10)
                print | ("Closing Browser..")
                self.driver.close()

            if Topology == "4":
                # WAN and LAN on same network adapter + Data (iSCSI) on same network adapter as WAN and LAN
                driver.find_element_by_name("inpClusterManagementIpv4").clear()
                driver.find_element_by_name("inpClusterManagementIpv4").send_keys(self.mgmt_IP)
                Select(driver.find_element_by_xpath(
                    "//form[@id='connectivityForm']/div[2]/div/table[2]/tbody[2]/tr/td[2]/select")).select_by_visible_text(
                    "WAN and LAN on same network adapter")
                Select(driver.find_element_by_xpath(
                    "//form[@id='connectivityForm']/div[2]/div/table[2]/tbody[2]/tr[2]/td[2]/select")).select_by_visible_text(
                    "Data (iSCSI) on same network adapter as WAN and LAN")

                driver.find_element_by_name("inpIpv4Netmask").clear()
                driver.find_element_by_name("inpIpv4Netmask").send_keys("255.255.254.0")
                driver.find_element_by_name("input_1").clear()
                driver.find_element_by_name("input_1").send_keys(self.DG.strip())

                time.sleep(2)
                self.wait.until(EC.element_to_be_clickable((By.XPATH, "(//button[@type='button'])[2]")))
                driver.find_element_by_xpath("(//button[@type='button'])[2]").click()
                time.sleep(1000)
                driver.find_element_by_xpath("( // button[ @ type = 'button'])[2]").click()
                time.sleep(10)
                self.driver.close()
            if Topology == "5":
                # WAN and LAN on same network adapter + Data (iSCSI) on separate network adapter from WAN and LAN
                driver.find_element_by_name("inpClusterManagementIpv4").clear()
                driver.find_element_by_name("inpClusterManagementIpv4").send_keys(self.mgmt_IP)
                Select(driver.find_element_by_xpath(
                    "//form[@id='connectivityForm']/div[2]/div/table[2]/tbody[2]/tr/td[2]/select")).select_by_visible_text(
                    "WAN and LAN on same network adapter")
                Select(driver.find_element_by_xpath(
                    "//form[@id='connectivityForm']/div[2]/div/table[2]/tbody[2]/tr[2]/td[2]/select")).select_by_visible_text(
                    "Data (iSCSI) on separate network adapter from WAN and LAN")
                Select(driver.find_element_by_xpath(
                    "//form[@id='connectivityForm']/div[2]/div/table[2]/tbody[4]/tr/td/div/table[2]/tbody/tr/td[2]/select")).select_by_visible_text(
                    self.ISCSI_A)
                driver.find_element_by_name("inpIpv4Netmask").clear()
                driver.find_element_by_name("inpIpv4Netmask").send_keys("255.255.254.0")
                driver.find_element_by_xpath("(//input[@name='inpIpv4Netmask'])[2]").clear()
                driver.find_element_by_xpath("(//input[@name='inpIpv4Netmask'])[2]").send_keys("255.255.252.0")
                driver.find_element_by_name("input_1").clear()
                driver.find_element_by_name("input_1").send_keys(self.DG.strip())
                driver.find_element_by_name("input_10").clear()
                driver.find_element_by_name("input_10").send_keys(self.Data1_RPA1.strip())
                driver.find_element_by_name("input_12").clear()
                driver.find_element_by_name("input_12").send_keys(self.Data1_RPA2.strip())
                time.sleep(2)
                self.wait.until(EC.element_to_be_clickable((By.XPATH, "(//button[@type='button'])[2]")))
                driver.find_element_by_xpath("(//button[@type='button'])[2]").click()
                time.sleep(1000)
                driver.find_element_by_xpath("( // button[ @ type = 'button'])[2]").click()
                time.sleep(5)
                self.driver.close()

        def is_element_present(self, how, what):
            try:
                self.driver.find_element(by=how, value=what)
            except NoSuchElementException as e:
                return False
            return True

        def is_alert_present(self):
            try:
                self.driver.switch_to_alert()
            except NoAlertPresentException as e:
                return False
            return True

        def close_alert_and_get_its_text(self):
            try:
                alert = self.driver.switch_to_alert()
                alert_text = alert.text
                if self.accept_next_alert:
                    alert.accept()
                else:
                    alert.dismiss()
                return alert_text
            finally:
                self.accept_next_alert = True

        def tearDown(self):
            self.driver.quit()
            self.assertEqual([], self.verificationErrors)


    if __name__ == "__main__":
        unittest.main()
    sys.exit()

#name_list, ds_list, VLAN, net_list_RPAs, RPAs_IPs_list, netmask, gateway, ova_file, path
#print('vCenter IP: {}'.format(vcIp))
#print('Cluster hirarchy: {}'.format(mobOVA[clusterSelected-1]))
#print('ESX list: {}'.format(clusterDictESX.get(clusterSelected)))
#print('RPA name list: {}'.format(rpaNameList))
#print('RPA IP list: {}'.format(rpaIpList))
#print('Datastore list: {}'.format(ds))
#print('Management network vlan: {} or {}'.format(vlan[vlanSelected-1],clusterDictVlan[clusterSelected][vlanSelected-1]))
#print('OVA file: {}'.format(ova))


#======================= Get env info stop here =======================





#####  NEED TO FIX!!!

if selectedDHCP == 2: #Print RPAs IP in case DHCP was selected
    print('DHCP - RPA List:')
    for dataCenter in range(0, len(content.rootFolder.childEntity)):
        for rpa in range (0, len(content.rootFolder.childEntity[dataCenter].vmFolder.childEntity)):
            if content.rootFolder.childEntity[dataCenter].vmFolder.childEntity[rpa].name in rpaNameList:
                print (content.rootFolder.childEntity[dataCenter].vmFolder.childEntity[rpa].guest.ipAddress)


