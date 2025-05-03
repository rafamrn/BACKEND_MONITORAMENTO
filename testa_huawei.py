import requests

url = "https://la5.fusionsolar.huawei.com/thirdData/getDevHistoryKpi"

headers = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "xsrf-token": "n-thakth1fo7vxc57ytjrs5d1fepbxtiqpg5up493ws6ntqnbyqp2ntgpcfyo9qqbx1ec6899ijv9iarrupe9fqp2k5dfws6aqc8ljvys4kbfvhhmmir89ldo4lg056p9g"
}

body = {
    "devIds":"1000000033933581",
    "devTypeId":1,
    "startTime":1746154800000,
    "endTime":1746241200000
}

session = requests.Session()
response = session.post(url, json=body)

print(response.json())