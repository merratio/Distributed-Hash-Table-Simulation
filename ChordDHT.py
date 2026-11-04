#Oconnor Burton - 2108222 

import hashlib

class Node():

    def __init__(self, name, iden):
        self.iden = iden
        self.name = name
        self.next = None
        self.prev = None
        self.keys = {}
    
    def addKey(self, key, keyHash, node):
        print('Welcome to addKey')

        node.keys.update({key: keyHash})
        print('Node')
        print(node.iden)
        print('Keys')
        print(node.keys)

    def findKey(self, key, node, tail):
        print('Welocome to findkey')
        #loop through neighbours until key is found
        if not node.keys:
            return
        if(node.keys.get(key)):
            return node.iden
        else:
            if node == tail:
                return 

            node.findKey(key, node.next,tail)

        return node.iden
    
    def assignKey(self, key, node, keyHash):
        print('welcome to assignkey')
        if(node.iden < keyHash):
            node.assignKey(key,node.next, keyHash)
        else: 
            node.addKey(key, keyHash, node)
        return

class DataItem():
    def __init__(self, dataId, value):
        self.iden = dataId
        self.value = value
        self.key = None


class ChordNetwork():
    nodes  = {} #list of node and hash pairs
    #data = {} #list of data name and hash pairs

    def __init__(self, m=6):
        self.m = m

    def hashFunction(self, item):
        sha1Hash = hashlib.sha1(item.encode('utf-8')).hexdigest()
        return int(sha1Hash, 16) % (2 ** self.m)
        

    def keyLookUp(self, key):
        print('Welcome to keylookup')
        if next(iter(self.nodes)).findKey(key, next(iter(self.nodes)), next(reversed(self.nodes))):
            return next(iter(self.nodes)).findKey(key, next(iter(self.nodes)), next(reversed(self.nodes)))
        return


    def addNode(self, name):
        nodeHash = self.hashFunction(name)
        node = Node(name, nodeHash)
        
        if not self.nodes:
            self.nodes.update({node: nodeHash})
            return

        self.nodes.update({node: nodeHash})
        self.nodes = dict(sorted(self.nodes.items(), key=lambda item: item[1]))
        
        nodeItems = list(self.nodes.keys())
        
        for i in range(len(nodeItems)):
            if i == 0:
               nodeItems[i].next = nodeItems[i+1]
               nodeItems[i].prev = nodeItems[len(nodeItems)-1]
            if i > 0 and i < len(nodeItems)-1:
                nodeItems[i].next = nodeItems[i+1]
                nodeItems[i].prev = nodeItems[i-1]
            if i == len(nodeItems) -1:
                nodeItems[i].prev = nodeItems[i-1]
                nodeItems[i].next = nodeItems[0]
        
        #search if hash function already exist 
        #add node 
        #   -need to find where in the ring node belongs
        #       -use a function similar to findKey and when the hash is less than current key update curr prev and stuff
        #assignKeys
        return

    def removeNode():
        pass

    def addData(self, dataItem, node):
        print('Welcome to addData')
        key = self.hashFunction(dataItem) #Hash key
        if self.keyLookUp(key):#keylookup
            print('Key is already existing')
        node.assignKey(dataItem,node, key)#assignKeys
        return

  

chord = ChordNetwork(m=6)

chord.addNode('me')
chord.addNode('myself')
chord.addNode('him')



chord.addData('hello.file', next(iter(chord.nodes)))
chord.addData('helo.file', next(iter(chord.nodes)))
chord.addData('hllo.file', next(iter(chord.nodes)))

