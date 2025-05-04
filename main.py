from clients.huawei_client import ApiHuawei
from clients.deye_client import ApiDeye
from clients.isolarcloud_client import ApiSolarCloud
from config.settings import settings
from datetime import date

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
    api.login_solarcloud()
    api.get_usinas()

    # Pegue uma usina qualquer (a primeira da lista)
    usina = api.usinas_cache[0]
    ps_id = usina["ps_id"]
    print(f"🔧 Usina selecionada: {ps_id} - {usina['ps_name']}")

    # Agora buscar o ps_key usando getDeviceList
    url = api.base_url + "getDeviceList"
    body = {
        "appkey": api.appkey,
        "token": api.token_cache,
        "curPage": 1,
        "size": 10,
        "ps_id": ps_id,
        "device_type_list": [1],
        "lang": "_pt_BR"
    }
    res = api._post_with_auth(url, body)
    data = res.json()
    inversores = data.get("result_data", {}).get("pageList", [])

    if not inversores:
        raise ValueError("Nenhum inversor encontrado para essa usina.")

    ps_key = inversores[0].get("ps_key")
    if not ps_key:
        raise ValueError("ps_key não encontrado no inversor.")

    data_str = date.today().strftime("%Y-%m-%d")

    print(f"✅ ps_key encontrado: {ps_key}")
    geracao = api.get_geracao_dia(data=data_str, ps_key=ps_key)

    for ponto in geracao:
        print(ponto)

def testar_deye():
    api = ApiDeye(settings.DEYE_USER, settings.DEYE_PASS, settings.DEYE_APPID, settings.DEYE_APPSECRET)
    token = api.fazer_login()
    if token:
        # usinas = api.get_usinas()
        usinas = api.get_geracao()
        print("Deye usinas:", usinas)
    else:
        print("Falha ao autenticar Deye")


if __name__ == "__main__":
    # Altere aqui para escolher qual testar
    testar_sungrow()
    # testar_huawei()
    # testar_deye()