from clients.huawei_client import ApiHuawei
from clients.deye_client import ApiDeye
from clients.isolarcloud_client import ApiSolarCloud
from config.settings import settings


def testar_huawei():
    api = ApiHuawei(settings.HUAWEI_USER, settings.HUAWEI_PASS)
    token = api.login_huawei()
    if token:
        usinas = api.get_geracao()
        print("Huawei usinas:", usinas)
    else:
        print("Falha ao autenticar Huawei")

def testar_sungrow():
    api = ApiSolarCloud(settings.ISOLAR_USER, settings.ISOLAR_PASS)
    token = api.login_solarcloud()
    if token:
        usinas = api.get_usinas()
        ps_keys = api.get_geracao()
        print("PS KEYS:", ps_keys)
        # print("Sungrow usinas:", usinas)
    else:
        print("Falha ao autenticar Sungrow")

def testar_deye():
    api = ApiDeye(settings.DEYE_USER, settings.DEYE_PASS, settings.DEYE_APPID, settings.DEYE_APPSECRET)
    token = api.fazer_login()
    if token:
        usinas = api.get_usinas()
        # usinas = api.get_geracao()
        print("Deye usinas:", usinas)
    else:
        print("Falha ao autenticar Deye")


if __name__ == "__main__":
    # Altere aqui para escolher qual testar
    testar_sungrow()
    # testar_huawei()
    # testar_deye()