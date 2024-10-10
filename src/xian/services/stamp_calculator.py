from contracting.stdlib.bridge.decimal import ContractingDecimal
from xian.constants import Constants
from contracting.execution.executor import Executor
from contracting.storage.driver import Driver
from contracting.stdlib.bridge.time import Datetime
from datetime import datetime
from xian.utils.tx import format_dictionary
import secrets
import socket
import pathlib
import json
import struct

# Ensure that ContractingInteger is correctly imported from your codebase
# from contracting.stdlib.bridge.integer import ContractingInteger

def safe_repr(obj, max_len=1024):
    try:
        r = repr(obj)
        # Remove memory address from representation if present
        rr = r.split(' at 0x')
        if len(rr) > 1:
            return rr[0] + '>'
        return rr[0][:max_len]
    except Exception:
        return None

class StampCalculator:
    def __init__(self):
        self.constants = Constants()

    def setup_socket(self):
        # If the socket file exists, remove it
        STAMPESTIMATOR_SOCKET = pathlib.Path(self.constants.STAMPESTIMATOR_SOCKET)
        if STAMPESTIMATOR_SOCKET.exists():
            STAMPESTIMATOR_SOCKET.unlink()

        # Create a socket
        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.socket.bind(self.constants.STAMPESTIMATOR_SOCKET)
        self.socket.listen(1)

    def listen(self):
        print('Listening...')
        while True:
            connection, client_address = self.socket.accept()
            print("Client connected")
            try:
                while True:
                    try:
                        # Read message length (4 bytes)
                        raw_msglen = connection.recv(4)
                        if not raw_msglen:
                            break
                        msglen = struct.unpack('>I', raw_msglen)[0]

                        # Read the message data
                        data = b''
                        while len(data) < msglen:
                            packet = connection.recv(msglen - len(data))
                            if not packet:
                                break
                            data += packet

                        if not data:
                            # No more data from client, client closed connection
                            print("Client disconnected")
                            break

                        print(f"Received: {data.decode()}")

                        tx = data.decode()
                        tx = json.loads(tx)

                        try:
                            response = self.execute(tx)
                            # Use custom encoder for JSON serialization
                            response_json = json.dumps(response, default=self.json_encoder)
                            response_bytes = response_json.encode()
                            message_length = struct.pack('>I', len(response_bytes))
                            connection.sendall(message_length + response_bytes)
                        except BrokenPipeError:
                            print("Cannot send data, broken pipe.")
                            break
                    except ConnectionResetError:
                        print("Client disconnected")
                        break
            finally:
                # Clean up the connection
                print("Client disconnected")
                connection.close()

    def generate_environment(self, input_hash='0' * 64, bhash='0' * 64, num=1):
        now = Datetime._from_datetime(datetime.now())
        return {
            'block_hash': self.generate_random_hex_string(),
            'block_num': num,
            '__input_hash': self.generate_random_hex_string(),
            'now': now,
            'AUXILIARY_SALT': self.generate_random_hex_string()
        }

    def generate_random_hex_string(self, length=64):
        # Generate a random number with `length//2` bytes and convert to hex
        return secrets.token_hex(nbytes=length // 2)

    def execute_tx(self, transaction, stamp_cost, environment: dict = {}, driver=None, executor=None):
        balance = 9999999
        output = executor.execute(
            sender=transaction['payload']['sender'],
            contract_name=transaction['payload']['contract'],
            function_name=transaction['payload']['function'],
            stamps=balance * stamp_cost,
            stamp_cost=stamp_cost,
            kwargs=transaction['payload']['kwargs'],
            environment=environment,
            auto_commit=False,
            metering=True
        )

        executor.driver.flush_cache()

        writes = [{'key': k, 'value': v} for k, v in output['writes'].items()]

        tx_output = {
            'transaction': transaction,
            'status': output['status_code'],
            'state': writes,
            'stamps_used': output['stamps_used'],
            'result': safe_repr(output['result'])
        }

        # Since we're using integers now, we can remove stringify_decimals
        tx_output = format_dictionary(tx_output)

        return tx_output

    def execute(self, transaction):
        driver = Driver(storage_home=self.constants.STORAGE_HOME)
        executor = Executor(
            metering=False,
            bypass_balance_amount=True,
            bypass_cache=True,
            driver=driver
        )
        environment = self.generate_environment()
        try:
            stamp_cost_var = executor.driver.get_var(contract='stamp_cost', variable='S', arguments=['value'])
            stamp_cost = int(stamp_cost_var)
        except:
            stamp_cost = 20
        return self.execute_tx(
            transaction=transaction,
            environment=environment,
            stamp_cost=stamp_cost,
            driver=driver,
            executor=executor
        )

    def json_encoder(self, obj):
        if isinstance(obj, Datetime):
            return obj.isoformat()
        elif isinstance(obj, ContractingDecimal):
            return str(obj)
        elif isinstance(obj, datetime):
            return obj.isoformat()
        else:
            return safe_repr(obj)

if __name__ == '__main__':
    sc = StampCalculator()
    sc.setup_socket()
    sc.listen()
