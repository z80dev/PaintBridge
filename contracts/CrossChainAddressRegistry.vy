# pragma version ^0.4.0

sonic_address: public(HashMap[address, address])

@external
def set_sonic_address(sonic_address: address):
    self.sonic_address[msg.sender] = sonic_address
