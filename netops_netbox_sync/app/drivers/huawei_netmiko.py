from netmiko import ConnectHandler


class HuaweiNetmikoDriver:
    def __init__(self, host: str, username: str, password: str, port: int = 22):
        self.params = {
            "device_type": "huawei",
            "host": host,
            "username": username,
            "password": password,
            "port": port,
            "fast_cli": False,
        }
        self.conn = None

    def open(self):
        self.conn = ConnectHandler(**self.params)

    def close(self):
        if self.conn:
            self.conn.disconnect()

    def send_command(self, command: str, read_timeout: int = 90) -> str:
        if not self.conn:
            raise RuntimeError("Conexão não iniciada")
        return self.conn.send_command(command, read_timeout=read_timeout)