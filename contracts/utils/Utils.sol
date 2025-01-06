// SPDX-License-Identifier: MIT

pragma solidity >=0.8.7 <0.9.0;

library AddressByteUtil {
    function toBytes32(address addr) internal pure returns (bytes32) {
        return bytes32(uint256(uint160(addr)));

    }
}

library Byte32AddressUtil {
    function toAddress(bytes32 b) internal pure returns (address) {
        return address(uint160(uint256(b)));
    }

}
