import hashlib
import json
from time import time
from urllib.parse import urlparse
from uuid import uuid4
import requests
from flask import Flask, jsonify, request, render_template, redirect, url_for
class Block:
    def __init__(self, index=None, transactions=None, timestamp=None, previous_hash=None):
        self.index = index
        self.transactions = transactions
        self.timestamp = timestamp
        self.previous_hash = previous_hash
        self.difficulty = 2
        self.nonce = 0
        self.merkle_hash = 0
    def save_list(self):
        result_chain = [self.index, self.transactions, \
                self.timestamp, self.previous_hash, self.difficulty, self.nonce, self.merkle_hash]
        return result_chain
    def restore_from_list(self, result_chain):
        self.index = result_chain[0]
        self.transactions = result_chain[1]
        self.timestamp = result_chain[2]
        self.previous_hash = result_chain[3]
        self.difficulty = result_chain[4]
        self.nonce = result_chain[5]
        self.merkle_hash = result_chain[6]
        
    def get_hash(self):
        info = f'{self.index}{self.timestamp}{self.merkle_hash}\
            {self.previous_hash}{self.nonce}'.encode()
        # dumnped  = json.dumps(self.__dict__, sort_keys=True).encode()
        return hashlib.sha256(info).hexdigest()
 

class Blockchain:
    def __init__(self):
        self.current_transactions = []
        self.chain = []
        self.nodes = set()
        self.genesis_block = Block(index=1, timestamp=time(), transactions=[]\
            , previous_hash=100)
        self.chain.append(self.genesis_block)
        self.level_of_difficulty = 2
        
    def get_merkle_hash(self, transactions):
        new_data = []
        if len(transactions)==0:
            return None
        if len(transactions)==1:
            # return transactions[0]
            info = f'{transactions[0]}'.encode()
            return hashlib.sha256(info).hexdigest()
        for i in range(0, len(transactions)-1, 2):
            combined = transactions[i] + transactions[i+1]
            combined_hash = hashlib.sha256(combined.encode()).hexdigest()
            new_data.append(combined_hash)
        if len(transactions) % 2 == 1:
            new_data.append(transactions[-1])
        return self.get_merkle_hash(new_data)

    def get_block_hash(self, block):
        info = f'{block.index}{block.timestamp}{block.merkle_hash}\
            {block.previous_hash}{block.nonce}'.encode()
        return hashlib.sha256(info).hexdigest()
   
    def add_block(self, block):
        previous_hash = self.get_block_hash(self.chain[-1])
        #valid proof
        
        #validate merkle hash
        merkle_hash = self.get_merkle_hash([transactions['hash'] for transactions in block.transactions])
        block_hash = self.get_block_hash(block)
        if block_hash[:self.level_of_difficulty]== "0"*self.level_of_difficulty\
            and previous_hash==block.previous_hash and merkle_hash==block.merkle_hash:
            self.current_transactions = []
            self.chain.append(block)
            print("add block success!")
            return True
        return False
    
    def valid_blockchain(self, chain):
        last_block = chain[0]
        current_index = 1
        while current_index < len(chain):
            block = chain[current_index]
            print(f'{last_block}')
            print(f'{block}')
            print("\n-----------\n")
            # Check that the hash of the block is correct
            last_block_hash = self.get_block_hash(last_block)
            if block.previous_hash != last_block_hash:
                return False

            # Check that the Proof of Work is correct
         
            block_hash = self.get_block_hash(block)
            merkle_hash = self.get_merkle_hash([transactions['hash'] for transactions in block.transactions])
            if merkle_hash != block.merkle_hash:
                print("merkle hash not matched!")
                print("transactions: ", block.transactions)
                print("merkle hash: ", merkle_hash)
                return False
            if block_hash[:self.level_of_difficulty]!= "0"*self.level_of_difficulty:
                print("difficulty not matched!")
                return False
            #validate merkle hash
            last_block = block
            current_index += 1
        print("validate success!")
        return True
       
    def register_node(self, address):
        """
        Add a new node to the list of nodes
        :param address: Address of node. Eg. 'http://192.168.0.5:5000'
        """
        parsed_url = urlparse(address)
        if parsed_url.netloc:
            self.nodes.add(parsed_url.netloc)
        elif parsed_url.path:
            # Accepts an URL without scheme like '192.168.0.5:5000'.
            self.nodes.add(parsed_url.path)
        else:
            raise ValueError('Invalid URL')


    def resolve_conflicts(self):
        neighbours = self.nodes
        new_chain = None
        max_length = len(self.chain)
        
        for node in neighbours:
            print("getting: ", node)
            response = requests.get(f'http://{node}/jsonify_chain')
            print("verifying", response.status_code )
            if response.status_code == 200:
                length = response.json()['length']
                print("length: ", length)
                chain = response.json()['chain']
                for i in range(len(chain)):
                    new_block = Block()
                    new_block.restore_from_list(chain[i])
                    chain[i] = new_block
                # Check if the length is longer and the chain is valid
                print("validating", self.valid_blockchain(chain))
                if length > max_length and self.valid_blockchain(chain):
                    max_length = length
                    new_chain = chain
                    print("new chain")
        # Replace our chain if we discovered a new, valid chain longer than ours
        if new_chain:
           
            #recycle the transactions
            current_index = 1
            while current_index < min(len(self.chain), len(new_chain)):
                if self.chain[current_index].get_hash() != new_chain[current_index].get_hash():
                    for trans in self.chain[current_index].transactions:
                        if trans['sender'] == "0":
                            continue
                        if self.check_transaction(trans['hash'], new_chain)==False:
                            #not already in another c
                            self.current_transactions.append(trans)
                current_index+=1
            self.chain = new_chain    
            return True

        return False



    def new_transaction(self, sender, recipient, amount):
        info = f'{sender}{recipient}{amount}'.encode()
        transaction_hash = hashlib.sha256(info).hexdigest()
        self.current_transactions.append({
            'sender': sender,
            'recipient': recipient,
            'amount': amount,
            'hash': transaction_hash,
        })
        return self.chain[-1].index + 1

    def confirm_transactions(self, transaction_hash):
        current_index = 1
        while current_index < len(self.chain):
            block = self.chain[current_index]
            for transaction in block.transactions:
                if transaction['hash'] == transaction_hash:
                    if len(self.chain)-current_index>=5:
                        return True
            current_index+=1
        return False
    def check_transaction(self, transaction_hash, new_chain):
        current_index = 1
        while current_index < len(new_chain):
            block = new_chain[current_index]
            for transaction in block.transactions:
                if transaction['hash'] == transaction_hash:
                    return True
            current_index+=1
        return False
    
    def proof_of_work(self, new_block):
        """
        Simple Proof of Work Algorithm:

         - Find a number p' such that hash(pp') contains leading 4 zeroes
         - Where p is the previous proof, and p' is the new proof
         
        :param last_block: <dict> last Block
        :return: <int>
        """
        new_block.nonce = 0
        computed_hash = self.get_block_hash(new_block)
        while not computed_hash[:self.level_of_difficulty]\
            == "0"*self.level_of_difficulty:
            new_block.nonce += 1
            computed_hash = self.get_block_hash(new_block)
        return computed_hash



# Instantiate the Node
app = Flask(__name__)
# Generate a globally unique address for this node
node_identifier = str(uuid4()).replace('-', '')
# Instantiate the Blockchain
blockchain = Blockchain()
@app.route('/jsonify_chain', methods=['GET'])
def jsonify_chain():
    print("get full json chain\n")
    result_chains = []
    for block in blockchain.chain:
        result_chains.append(block.save_list())
    response = {
        'chain': result_chains,
        'length': len(blockchain.chain),
    }
    return jsonify(response), 200

@app.route('/mine', methods=['GET'])
def mine():
    last_block = blockchain.chain[-1]
    new_block = Block(index=last_block.index+1, \
        transactions=blockchain.current_transactions,\
        timestamp=time(),\
        previous_hash=last_block.get_hash())
    new_block.transactions = blockchain.current_transactions
    new_block.difficulty = blockchain.level_of_difficulty
   
    info = f'{"0"}{node_identifier}{1}'.encode()
    transaction_hash = hashlib.sha256(info).hexdigest()
    new_block.transactions.append({
            'sender': "0",
            'recipient': node_identifier,
            'amount': 1,
            'hash': transaction_hash,
        }
    )
    print(new_block.transactions)
    new_block.merkle_hash = blockchain.get_merkle_hash([transactions['hash'] for transactions in new_block.transactions])
    computed_hash = blockchain.proof_of_work(new_block)
    added = blockchain.add_block(new_block)
    
    if added:
        response = {
            'message': "New Block Forged",
            'index': new_block.index,
            'transactions': new_block.transactions,
            'proof': new_block.get_hash(),
            'previous_hash': new_block.previous_hash,
        }
        # return jsonify(response), 200
        return render_template('mine.html', **response)

    response = {'messagae:': "mine failed, please retry"}
    # return jsonify(response), 200
    return render_template('mine.html', **response)


@app.route('/transactions/new', methods=['Get', 'POST'])
def new_transaction():
    
    if request.method == 'POST':
        values = request.get_json()
        sender = request.form.get('sender')
        recipient = request.form.get('recipient')
        amount = request.form.get('amount')
        print(sender, recipient, amount)
        if sender is None or recipient is None or amount is None:
            response = {'message': 'Missing values'}
            return render_template('transaction.html', **response)
        # Create a new Transaction
        index = blockchain.new_transaction(sender, recipient, amount)
        response = {'message': f'Transaction will be added to Block {index}'}
        return render_template('transaction.html', **response)
    return render_template('transaction.html')
   

@app.route('/chain', methods=['GET'])
def full_chain():
    print("get full chain\n")
    result_chains = []
    for block in blockchain.chain:
        result_chains.append(block.save_list())
    response = {
        'chain': result_chains,
        'length': len(blockchain.chain),
    }
    for chain in result_chains:
        # only show first 6 digits of hash
        if isinstance(chain[3], str) and len(chain[3]) > 6:
            chain[3] = chain[3][:6]
        if isinstance(chain[6], str) and len(chain[6]) > 6:
            chain[6] = chain[6][:6]
    return render_template('chain.html', response=response)


@app.route('/register', methods=['GET','POST'])
def register_nodes():
    if request.method == 'POST':
        # 处理表单提交
        url = request.form.get('url')
        if url is None:
            return "Error: Please supply a valid list of nodes", 400
        blockchain.register_node(url)
        print("redirecting: ", url)
        return  render_template('registered.html')
    return render_template('register.html')


@app.route('/resolve', methods=['GET'])
def consensus():
    print("reaching consensus")
    replaced = blockchain.resolve_conflicts()
    result_chains = []
    for chain in blockchain.chain:
        result_chains.append([chain.index, chain.transactions, chain.timestamp, \
            chain.previous_hash, chain.nonce, chain.merkle_hash])
    for chain in result_chains:
        print(chain)
        if isinstance(chain[3], str) and len(chain[3]) > 6:
            chain[3] = chain[3][:6]
        if isinstance(chain[5], str) and len(chain[5]) > 6:
            chain[5] = chain[5][:6]
    return render_template('conflict.html', replaced=replaced, chain_list=result_chains)

if __name__ == '__main__':
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=9871, type=int, help='port to listen on')
    args = parser.parse_args()
    port = args.port

    app.run(host='0.0.0.0', port=port,threaded=True)

