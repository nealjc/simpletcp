## simpletcp
Small library to easily allow TCP communication between Python programs.

The library does the following:
  * Turns the TCP socket interface into one method call for client and server
  * Handles basic network issues like short reads/writes, disconnects
  * Turns TCP into a message oriented stream rather than byte stream (adds
    length headers for you)

The library is NOT:
  * Production level
  * A generic TCP client or server. The client and server are only
    compatible with one another.
  * Meant to be a replacement for libraries like Twisted    

###Sample Usage
####Client
```python
from simpletcp import create_client

cli = create_client('localhost', 8080)
cli.send_msg('hey there')
cli.close()
```

####Server
```python
from simpletcp import create_server

def msg_received(address, msg):
    print "{0} said: {1}".format(address,
                                msg)

create_server(8080, msg_received)
raw_input("Enter a key to quit\n")
```