from scrapli.driver.core import GenericDriver


class HuaweiScrapliDriver:
    def __init__(self, host: str, username: str, password: str, port: int = 22):
        self.device = {
            "host": host,
            "auth_username": username,
            "auth_password": password,
            "auth_strict_key": False,
            "platform": "huawei_vrp",
            "port": port,
        }
        self.conn = None

    def open(self):
        self.conn = GenericDriver(**self.device)
        self.conn.open()

    def close(self):
        if self.conn:
            self.conn.close()

    def send_command(self, command: str) -> str:
        if not self.conn:
            raise RuntimeError("Conexão não iniciada")
        response = self.conn.send_command(command)
        return response.result