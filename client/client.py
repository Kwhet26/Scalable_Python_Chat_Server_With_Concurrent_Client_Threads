import json
import socket
import sys
import threading
import ast

# --------- Json String Formats --------- 

def connnect_json(user_name: str, chatRooms: list):
    if not user_name.startswith('@'):
        user_name = '@' + user_name

    # Check for # symbol
    for i in range(len(chatRooms)):
        if not chatRooms[i].startswith('#'):
            chatRooms[i] = '#' + chatRooms[i]   
                  
    data = {
        "action": "connect",
        "user_name": user_name,
        "targets": chatRooms
    }
    
    # returns json string
    return json.dumps(data)

def send_message_json(user_name: str, target: str, message: str, person: bool):
    if not user_name.startswith('@'):
        user_name = '@' + user_name
        
    # Target: Place @ for person and # for chat room
    if (person):
        if not target.startswith('@'):
            target = '@' + target
    else:
        if not target.startswith('#'):
            target = '#' + target
    
    data = {
        "action": "message",
        "user_name": user_name,
        "target": target,
        "message": message
    }
    
    return json.dumps(data)
    

def disconnect_json():
    data = {
        "action": "disconnect"
    }
    
    return json.dumps(data)

def server_shutdown_json():
    data = {
        "status": "disconnect"
    }
    
    return json.dumps(data)


# --------- Main Functions: Listen(), User_Input, Main() ---------
def quit():
    global connection
    global stop_listen_thread

    try:
        print("\nDisconnecting from server.")
        m = disconnect_json()
        m_encoded = bytes(m, 'UTF-8')
        connection.send(m_encoded)
    except Exception as e:
        print("\nERROR Quitting: ", e)
    finally:
        stop_listen_thread = True  # Signal the listening thread to exit
        connection.shutdown(socket.SHUT_RDWR)
        connection.close()
        connection = None  # Set the connection to None after closing
        print("\nConnection Closed.")
        sys.exit(0)  # Exit the program


def listen(): # Listens to the server for new messages
    global connection
    global u_name
    global stop_listen_thread
    print("\nNow Listening to server for messages...")
    while (not stop_listen_thread):
        try:
            data = connection.recv(4096).decode('UTF-8')
            if (data):
                data = json.loads(data)
                if (data["status"] == "disconnect"):
                    print("Server disconnecting...")
                    quit()
                elif (data["status"] == "error"):
                    print("Error from server: ", data["message"])
                elif (data["status"] == "chat"):
                    for message in data["history"]:
                        # temp = ast.literal_eval(message) # commented out for bug
                        temp = message
                        sender = temp["from"]
                        target = temp["target"]
                        text = temp["message"]
                        print(f"{sender} -> {target}: {text}")
                else:
                    print("\nERROR: Receieved data but didn't match any of the types!")
        except socket.error:
            break
        
def user_input(): # Listens to the keyboard to check if the client/user is trying to send a message
    global connection
    global u_name
    try:
        while True:
            message = input().strip()
            index = message.find(' ')
            
            if index != -1:
                target = message[:index]
                message = message[index + 1:]
                
                if message:
                    if target.startswith('@'):
                        if (sys.getsizeof(message) > 3800): # Checks if message is too large
                            print("\nERROR: Invalid message due to the message being too large!")
                        else:
                            j = send_message_json(u_name, target, message, True)
                            j_encoded = bytes(j, 'UTF-8')
                            try:
                                connection.send(j_encoded)
                            except Exception as e:
                                print("\nSend Error:", e)
                            
                    elif target.startswith('#'):
                        if (sys.getsizeof(message) > 3800): # Checks if message is too large
                            print("\nERROR: Invalid message due to the message being too large!")
                        else:
                            j = send_message_json(u_name, target, message, False)
                            j_encoded = bytes(j, 'UTF-8')
                            try:
                                connection.send(j_encoded)
                            except Exception as e:
                                print("\nSend Error:", e)
                    else:
                        print("\nError: Target must start with '@' or '#'")
                else:
                    print("\nError: No message provided")
            else:
                print("\nInvalid Format: @User_Name or #ChatRoom then message")
    except KeyboardInterrupt as k:
        quit()            
        
    

def main(ip, port):
    global connection
    global u_name
    global stop_listen_thread

    # Connection:
    connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    target_chat_rooms = []  # Declare target_chat_rooms as a global variable

    
    address = (ip, port)
    try:
        connection.connect(address)
    
        u_name_bool: bool = True
        
        while (u_name_bool):
            u_name = input("\nEnter your username: ")
            if (sys.getsizeof(u_name) > 60):
                print("\nERROR: Username is too large!")
            else:
                u_name_bool = False
            
        number_rooms = int(input("\nEnter number of rooms you want to join: "))
        
        for i in range(number_rooms):
            size_check: bool = True
            while (size_check):
                r: str = input(f"\nEnter name of room {i + 1}: ").strip()
                if (sys.getsizeof(r) > 60):
                    print("\nERROR: Chat Room name is too large!")
                else:
                    target_chat_rooms.append(r)
                    size_check = False
        intial_message = connnect_json(u_name, target_chat_rooms)
        encoded = bytes(intial_message, 'UTF-8')
        
        try:
            connection.send(encoded)
        except Exception as e:
            print("\nListen Send ERROR: ", e)   
         
        stop_listen_thread = False
        listen_thread = threading.Thread(target=listen, daemon=True)
        listen_thread.start()
        user_input() # User_Input for messages
    
    except Exception as e:
        print("\nERROR: ", e)
    
# Runs main function    
main(sys.argv[1], int(sys.argv[2]))