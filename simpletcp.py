"""
simpletcp is a small library that simplifies writing networking code.
It is not as robust nor does it have as many features as a framework
like Twisted.

The library does the following:

"""
import SocketServer
import socket
import zlib
import threading
import struct

class SimpleTCPServerHandler(SocketServer.BaseRequestHandler):

    def setup(self):
        print "New connection from", self.client_address

    def handle(self):
        while True:
            #read header for length
            try:
                length = struct.unpack("!i", self.read_all(4))[0]
            except:
                #client closed normally
                break
            try:
                #read entire message
                data = self.read_all(length)
            except:
                #client shouldn't have closed here. error handler
                break
            #callback
            if self.server._decompress_func:
                data = self.server._decompress_func(data)
            self.server._call_back(self.client_address, data)
        print "Client {0} went away".format(self.client_address)

    def read_all(self, length):
        remaining = length
        msg = ""
        while remaining > 0:
            read = self.request.recv(remaining)
            if not read:
                raise Exception("Connection terminated")
            msg += read
            remaining -= len(read)
        return msg

class ThreadedTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, addr, handler, call_back, new_conn_cb, conn_closed_cb,
                 decompress_func):
        SocketServer.TCPServer.__init__(self, addr, handler)
        self._call_back = call_back
        self._new_cb = new_conn_cb
        self._closed_cb = conn_closed_cb
        self._decompress_func = decompress_func

#could try re-connecting in send_msg if the connection dies
#still raise an excepiton, but on next call try to re-connect
#so the object is still valid
class TCPSender(object):

    def __init__(self, dest_addr, port, compress_func, timeout):
        self._socket = socket.socket(socket.AF_INET,
                                     socket.SOCK_STREAM)
        self._socket.connect((dest_addr, port))
        self._compress_func = compress_func

    def send_msg(self, msg):
        if self._compress_func:
            msg = self._compress_func(msg)
        msg_len = len(msg)
        try:
            self.write_all(struct.pack("!i", msg_len))
            self.write_all(msg)
        except:
            print "Error"

    def close(self):
        self._socket.close()

    def write_all(self, msg):
        to_send = len(msg)
        sent = 0
        while True:
            sent += self._socket.send(msg)
            if sent == to_send:
                break
            if sent == 0:
                raise Exception("Connection terminated")
            msg = msg[sent:]

def create_server(listen_port, new_msg_cb, decompress_func=zlib.decompress):
    """Creates and starts a server listening on port listen_port. When
    a new message is (fully) received, new_msg_cb will be called
    with the message
    """
    server = ThreadedTCPServer(('localhost', listen_port),
                               SimpleTCPServerHandler,
                               new_msg_cb, None, None,decompress_func)
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.setDaemon(True)
    server_thread.start()

def create_client(dest_addr, port, compress_func=zlib.compress,
                  timeout=5):
    sender = TCPSender(dest_addr, port, compress_func, timeout)
    return sender

#make this include client address?
def msg_test(cli_addr, msg):
    print cli_addr, msg
    
if __name__ == '__main__':
    import time
    create_server(8080, msg_test)

    time.sleep(1)
    cli = create_client('localhost', 8080)
    while True:
        cli.send_msg("testing")
        try:
            time.sleep(2)
        except:
            break
