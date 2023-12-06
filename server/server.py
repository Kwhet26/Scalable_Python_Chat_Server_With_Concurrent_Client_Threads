import socket
import json
import select
import sys

clients = {} # client dictionary
chat_rooms = {} # Opened chatrooms
message_que = [] # Used to que messages

def send_message(msg):
    target = msg['target']
    if (target[0] == "@"):
        for c in clients:
            user_name, _ = clients[c]
            if (target == user_name): # send message
                data = json.dumps({
                    "status": "chat",
                    "history": [
                        {
                            "target": target,
                            "from": msg['user_name'],
                            "message": msg['message']
                        }
                    ]
                })
                c.send(data.encode('utf-8'))        
        
    elif (target[0] == "#"):
        if (target in chat_rooms):
            data = json.dumps({
                "status": "chat",
                "history": [
                    {
                        "target": target,
                        "from": msg['user_name'],
                        "message": msg['message']
                    }
                ]
            })
            for c in chat_rooms[target]:
                u_name, _ = clients[c]
                if (u_name != msg['user_name']): # Make sure we don't send back to self
                    c.send(data.encode('utf-8'))
    else:
        print(f"\nInvalid Message Error Tossing that message...")
        
def close_all_connections():
    shut_down_json = json.dumps({
        "status": "disconnect"
    }).encode('utf-8')
    
    for c in clients:
        user_name, _ = clients[c]
        print(f"\nClosing {user_name}'s connection.")
        c.send(shut_down_json)
        c.close()
        
def send_error(client, error):
    user_name, _ = clients[client]
    print(f"\nSending Error: {error} to {user_name}")
    data = json.dumps({
        "status": "error",
        "message": error
    }).encode('utf-8')
    client.send(data)
    
def remove_from_chat_room(s, targets):
    for t in targets:
        chat_rooms[t].remove(s)
        if (len(chat_rooms[t]) == 0): # Check if empty
            del chat_rooms[t]
            print(f"\nDeleted empty chat room {t}")
        

def main(HOST, PORT):
    # Create a socket for the server
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((HOST, PORT))
    server_socket.listen()
    print(f"\nServer Listening on {HOST}, {PORT}")
    connections = [server_socket]
    
    try:
        while True:
            sockets, _, _ = select.select(connections, [], [])
            
            for s in sockets:
                if (s is server_socket):
                    client_socket, client_addr = server_socket.accept()
                    connections.append(client_socket)
                    print(f"\nNew Inital Connection: {client_addr}")
                    
                else:
                    try:
                        data = data = s.recv(4096).decode('utf-8')
                        data = json.loads(data)
                        
                        if (data['action'] == 'connect'):
                            targets = data['targets']
                            user_name = data["user_name"]
                            clients[s] = (user_name, targets)
                            print(f"\nNew Client connected with username {user_name} and {targets}")
                            
                            # Check to see if targets exists in chat_room
                            for room in targets:
                                if room in chat_rooms:
                                    chat_rooms[room].append(s)  # appends the connection to that room
                                    print(f"\nAdded {user_name} to {room}")
                                else:
                                    room_data = [s]
                                    chat_rooms[room] = room_data
                                    print(f"\nNew chat room created: {room} by {user_name}")

                        elif (data['action'] == 'message'):
                            message_que.append(data)
                            
                        elif (data['action'] == 'disconnect'):
                            if s in clients:
                                user_name, user_chat_rooms = clients[s]
                                remove_from_chat_room(s, user_chat_rooms)
                                print(f"\n{user_name} is disconnecting from the server.")
                                del clients[s]
                            connections.remove(s)
                            s.close()
                            
                        
                        for msg in message_que:
                            send_message(msg)
                                
                        message_que.clear() # Clears out the que once we sent everything
                    except UnicodeDecodeError:
                        send_error(s, "Malformed UTF-8 Data")
                    except json.JSONDecodeError:
                        send_error(s, "Malformed JSON")
                    except KeyError:
                        send_error(s, "Missing Required Field")
                    except ValueError:
                        send_error(s, "Message Longer Than 4096 Bytes")
    except KeyboardInterrupt:
        print("\nClosing server")
        close_all_connections()
    finally:
        server_socket.close()


main(sys.argv[1], int(sys.argv[2]))