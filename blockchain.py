import json
import pickle
import time
from hashlib import sha256
# Block class
# Block is a class that contains the data and the hash of the previous block
# The hash of the previous block is used to link the blocks together
# The hash of the block is used to verify the integrity of the chain
# We plan to use the blockchain to store the data
# Need to solve below issues:
# 1. In CRUD operations, we need to be able to add, read data
# 2. How to solve the conflicts
# 3. Performance of reading data, especially when the data is large and have many nodes
from os.path import exists

from decouple import config


class Block:
    def __init__(self, index, data, timestamp, previous_hash):
        self.index = index
        self.data = data
        self.timestamp = timestamp
        self.previous_hash = previous_hash
        self.nonce = 0

    def compute_hash(self):
        """
        A function that return the hash of the block contents.
        """
        block_string = json.dumps(self.__dict__, sort_keys=True)
        return sha256(block_string.encode()).hexdigest()


class Blockchain:
    # difficulty of our PoW algorithm
    difficulty = 2
    file_name = config("BLOCK_CHAIN_BACKUP", default='./blockchain.bk')

    def __init__(self):
        if exists(self.file_name):
            with open(self.file_name, 'rb') as f:
                self.chain = pickle.load(f)
        else:
            self.unconfirmed_data = []
            self.chain = []
            self.create_genesis_block()

    def dump_data(self):
        pickle.dump(self.chain, open(self.file_name, 'wb'))

    def create_genesis_block(self):
        """
        A function to generate genesis block and appends it to
        the chain. The block has index number 0, previous_hash as 0, and
        a valid hash.
        """
        genesis_block = Block(0, [], time.time(), "0")
        genesis_block.hash = genesis_block.compute_hash()
        self.chain.append(genesis_block)

    @property
    def last_block(self):
        return self.chain[-1]

    def add_block(self, block, proof):
        """
        A function that adds the block to the chain after verification.
        Verification includes:
        * Checking if the proof is valid.
        * The previous_hash referred in the block and the hash of last block
          in the chain match.
        """
        previous_hash = self.last_block.hash

        if previous_hash != block.previous_hash:
            return False

        if not self.is_valid_proof(block, proof):
            return False

        block.hash = proof
        self.chain.append(block)
        return True

    def is_valid_proof(self, block, block_hash):
        """
        Check if block_hash is valid hash of block and satisfies
        the difficulty criteria.
        """
        return (block_hash.startswith('0' * Blockchain.difficulty) and
                block_hash == block.compute_hash())

    def proof_of_work(self, block):
        """
        Function that tries different values of nonce to get a hash
        that satisfies our difficulty criteria.
        """
        block.nonce = 0

        computed_hash = block.compute_hash()
        while not computed_hash.startswith('0' * Blockchain.difficulty):
            block.nonce += 1
            computed_hash = block.compute_hash()

        return computed_hash

    def set_data(self, data):
        self.unconfirmed_data.append(data)

    @classmethod
    def check_chain_validity(cls, chain):
        result = True
        previous_hash = "0"

        for block in chain:
            block_hash = block.hash
            # remove the hash field to recompute the hash again
            # using `compute_hash` method.
            delattr(block, "hash")

            if not cls.is_valid_proof(block, block_hash) or \
                    previous_hash != block.previous_hash:
                result = False
                break

            block.hash, previous_hash = block_hash, block_hash

        return result

    def mine(self):
        """
        This function serves as an interface to add the pending
        transactions to the blockchain by adding them to the block
        and figuring out Proof Of Work.
        """
        if not self.unconfirmed_data:
            return False

        last_block = self.last_block

        new_block = Block(index=last_block.index + 1,
                          data=self.unconfirmed_data,
                          timestamp=time.time(),
                          previous_hash=last_block.hash)

        proof = self.proof_of_work(new_block)
        self.add_block(new_block, proof)

        self.unconfirmed_data = []
        return new_block.index
