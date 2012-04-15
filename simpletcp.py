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

    def handle(self):
        while True:
            #read header for length
            length = struct.unpack("!i", self.read_all(4))[0]
            #read entire message
            data = self.read_all(length)
            #callback
            if self.server._decompress_func:
                data = self.server._decompress_func(data)
            self.server._call_back(data)

    def read_all(self, length):
        remaining = length
        msg = ""
        while remaining > 0:
            read = self.request.recv(remaining)
            if not read:
                print "ERROR"
                break
            msg += read
            remaining -= len(read)
        return msg

class ThreadedTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, addr, handler, call_back, decompress_func):
        SocketServer.TCPServer.__init__(self, addr, handler)
        self._call_back = call_back
        self._decompress_func = decompress_func

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
        self.write_all(struct.pack("!i", msg_len))
        self.write_all(msg)

    def write_all(self, msg):
        to_send = len(msg)
        sent = 0
        while True:
            sent += self._socket.send(msg)
            if sent == to_send:
                break
            msg = msg[sent:]

def create_server(listen_port, new_msg_cb, decompress_func=zlib.decompress):
    """Creates and starts a server listening on port listen_port. When
    a new message is (fully) received, new_msg_cb will be called
    with the message
    """
    server = ThreadedTCPServer(('localhost', listen_port),
                               SimpleTCPServerHandler,
                               new_msg_cb, decompress_func)
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.setDaemon(True)
    server_thread.start()

def create_client(dest_addr, port, compress_func=zlib.compress,
                  timeout=5):
    sender = TCPSender(dest_addr, port, compress_func, timeout)
    return sender

#make this include client address?
def msg_test(msg):
    print msg
    
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
