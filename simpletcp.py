"""
simpletcp is a small library that simplifies writing networking code.
Meant for use to get a prototype up and running quickly. Definitely
not production-level code nor are there any features (see something like Twisted).

The library does the following:
  - Turns the TCP socket interface into one method call for client and server
  - Handles basic network issues like short reads/writes, disconnects
  - Turns TCP into a message oriented stream rather than byte stream (adds
    length headers for you)

The server is a threaded TCP server (one thread per request) and everything
is handled via callbacks (new clients, client messages, etc). User is
responsible for synchronization in the callback methods if necessary. 

The client blocking.

Only the create_server and create_client functions should be called directly.
Code hasn't really been tested much yet. 
"""
import SocketServer
import socket
import zlib
import threading
import struct

PROTOCOL_ERROR = 0
CONNECTION_CLOSED = 1

class SimpleTCPServerHandler(SocketServer.BaseRequestHandler):

    def setup(self):
        if self.server._new_cb:
            self.server._new_cb(self.client_address)

    def finish(self):
        if self.server._closed_cb:
            self.server._closed_cb(self.client_address, self._reason)

    def handle(self):
        self._reason = CONNECTION_CLOSED
        while True:
            #read header for length
            ret_code, data = self.read_all(4)
            if ret_code == 0 and not data:
                break
            elif ret_code == 1:
                self._reason = PROTOCOL_ERROR
                break
            length = struct.unpack("!i",data)[0]
            #read entire message
            ret_code, data = self.read_all(length)
            if ret_code == 1:
                self._reason = PROTOCOL_ERROR
                break
            if self.server._decompress_func:
                data = self.server._decompress_func(data)
            self.server._call_back(self.client_address, data)

    def read_all(self, length):
        """Blocks until length bytes are read from the socket.
        """
        remaining = length
        msg = ""
        while remaining > 0:
            read = self.request.recv(remaining)
            if not read and remaining == length:
                #client closed the connection normally
                return (0, "")
            elif not read:
                #error, connection closed while reading data
                return (1, "")
            msg += read
            remaining -= len(read)
        return (0, msg)

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

class NoConnection(Exception): pass
class ConnectionTerimated(Exception): pass

class TCPSender(object):

    def __init__(self, dest_addr, port, compress_func, timeout=5):
        """Creates a new TCPSender.

        timeout should be >= 1
        """
        self._compress_func = compress_func
        self._timeout = timeout
        self._host = dest_addr
        self._port = int(port)
        self._timeout = timeout
        self._connected = False

    def _try_connecting(self):
        try:
            self._socket = socket.socket(socket.AF_INET,
                                     socket.SOCK_STREAM)
            self._socket.settimeout(self._timeout)
            self._socket.connect((self._host, self._port))
            self._connected = True
        except socket.error as e:
            raise Exception("Unable to connect to your server {0}:{1} ({2})".format(
                self._host, self._port, e))

    def send_msg(self, msg):
        """Send a message to the simpletcp server. This method is blocking.
        If the method returns normally, the message was succesfully sent.

        Raises NoConnection if a connection cannot be established
        Raises ConnectionTerminated if an error occurred while writing the data

        This object can still be used if an exception was raised. It will
        try to re-establish a connection to the server if necessary. 
        """
        if not self._connected:
            self._try_connecting()
        if self._compress_func:
            msg = self._compress_func(msg)
        msg_len = len(msg)
        try:
            self._write_all(struct.pack("!i", msg_len))
            self._write_all(msg)
        except Exception as e:
            self._connected = False
            raise ConnectionTerimated(
                "Error writing to simpletcp server {0}".format(e))

    def close(self):
        """Close the connection to the server. Once this method is called,
        this object can no longer be used. 
        """
        self._socket.close()

    def _write_all(self, msg):
        to_send = len(msg)
        sent = 0
        while True:
            sent += self._socket.send(msg)
            if sent == to_send:
                break
            if sent == 0:
                raise Exception("Connection terminated")
            msg = msg[sent:]

def create_server(listen_port, new_msg_cb, new_conn=None, conn_closed=None,
                  decompress_func=zlib.decompress, same_thread=False):
    """Creates and starts a server listening on port listen_port. When
    a new message is (fully) received, new_msg_cb will be called
    with the message
    """
    server = ThreadedTCPServer(('', listen_port),
                               SimpleTCPServerHandler,
                               new_msg_cb, new_conn, conn_closed,
                               decompress_func)
    if not same_thread:
        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.setDaemon(True)
        server_thread.start()
    else:
        server.serve_forever()

def create_client(dest_addr, port, compress_func=zlib.compress,
                  timeout=5):
    """Returns a blocking client object with methods send_msg() and close().
    A connection with the server isn't established until the first send_msg()
    call. If a send_msg() call fails, it can be called again and a new
    connection will be attempted. 
    """
    sender = TCPSender(dest_addr, port, compress_func, timeout)
    return sender
