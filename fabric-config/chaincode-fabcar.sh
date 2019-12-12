#!/bin/bash
CURR_PWD=$PWD
BASEDIR=$(dirname "$0")
source $BASEDIR/setvars.sh

if [ -z ${ORDERER_ORG_DOMAIN+x} ]; then
  echo "ORDERER_ORG_DOMAIN is not set, exiting"
  exit 1;
elif [ -z ${ORG1_DOMAIN+x} ]; then
  echo "ORG1_DOMAIN is not set, exiting"
  exit 1;
elif [ -z ${ORG2_DOMAIN+x} ]; then
  echo "ORG2_DOMAIN is not set, exiting"
  exit 1;
fi

CHANNEL_NAME="$1"
: ${CHANNEL_NAME:="ibcchannel"}
echo "CHANNEL_NAME set to $CHANNEL_NAME"
export FABRIC_CFG_PATH=$CURR_PWD/$BASEDIR
export GOPATH=$FABRIC_CFG_PATH

echo "FABRIC_CFG_PATH is set to $FABRIC_CFG_PATH"

cd $BASEDIR

export CORE_PEER_TLS_ENABLED=true
export IBC_ORDERER_END_POINT=$ORDERER_ORG_DOMAIN:443
export IBC_PEER_ORG1_PEER0=peer-0.$ORG1_DOMAIN:443
export IBC_PEER_ORG1_PEER1=peer-1.$ORG1_DOMAIN:443
export IBC_PEER_ORG1_PEER2=peer-2.$ORG1_DOMAIN:443
export IBC_PEER_ORG2_PEER0=peer-0.$ORG2_DOMAIN:443
export IBC_PEER_ORG2_PEER1=peer-1.$ORG2_DOMAIN:443
export IBC_PEER_ORG2_PEER2=peer-2.$ORG2_DOMAIN:443
export IBC_ORG1_ADMIN_MSP=./crypto-config/peerOrganizations/$ORG1_DOMAIN/users/Admin@$ORG1_DOMAIN/msp
export IBC_ORG2_ADMIN_MSP=./crypto-config/peerOrganizations/$ORG2_DOMAIN/users/Admin@$ORG2_DOMAIN/msp
export CORE_PEER_TLS_ROOTCERT_FILE=./letsencrypt.pem

echo "Installing chaincode fabcar on all org1 peer nodes"
export CORE_PEER_LOCALMSPID="Org1MSP"
export CORE_PEER_MSPCONFIGPATH=$IBC_ORG1_ADMIN_MSP
export CORE_PEER_ADDRESS=$IBC_PEER_ORG1_PEER0
peer chaincode install -n fabcar -v 1.0 -l golang -p samplechaincode/fabcar/go/
export CORE_PEER_ADDRESS=$IBC_PEER_ORG1_PEER1
peer chaincode install -n fabcar -v 1.0 -l golang -p samplechaincode/fabcar/go/
export CORE_PEER_ADDRESS=$IBC_PEER_ORG1_PEER2
peer chaincode install -n fabcar -v 1.0 -l golang -p samplechaincode/fabcar/go/

echo "Installing chaincode fabcar on all org2 peer nodes"
export CORE_PEER_LOCALMSPID="Org2MSP"
export CORE_PEER_MSPCONFIGPATH=$IBC_ORG2_ADMIN_MSP
export CORE_PEER_ADDRESS=$IBC_PEER_ORG2_PEER0
peer chaincode install -n fabcar -v 1.0 -l golang -p samplechaincode/fabcar/go/
export CORE_PEER_ADDRESS=$IBC_PEER_ORG2_PEER1
peer chaincode install -n fabcar -v 1.0 -l golang -p samplechaincode/fabcar/go/
export CORE_PEER_ADDRESS=$IBC_PEER_ORG2_PEER2
peer chaincode install -n fabcar -v 1.0 -l golang -p samplechaincode/fabcar/go/

echo "Instantiating chaincode fabcar on the channel only once"
peer chaincode instantiate -o $IBC_ORDERER_END_POINT --tls --cafile $CORE_PEER_TLS_ROOTCERT_FILE -C $CHANNEL_NAME -n fabcar -l golang -v 1.0 -c '{"Args":[]}' -P 'AND ('\''Org1MSP.peer'\'','\''Org2MSP.peer'\'')'

sleep 30

echo "Invoking chaincode query on all org1 nodes"
export CORE_PEER_LOCALMSPID="Org1MSP"
export CORE_PEER_MSPCONFIGPATH=$IBC_ORG1_ADMIN_MSP
export CORE_PEER_ADDRESS=$IBC_PEER_ORG1_PEER0
peer chaincode query -C $CHANNEL_NAME -n fabcar -c '{"Args":["queryCar","a"]}'
export CORE_PEER_ADDRESS=$IBC_PEER_ORG1_PEER1
peer chaincode query -C $CHANNEL_NAME -n fabcar -c '{"Args":["queryCar","a"]}'
export CORE_PEER_ADDRESS=$IBC_PEER_ORG1_PEER2
peer chaincode query -C $CHANNEL_NAME -n fabcar -c '{"Args":["queryCar","a"]}'

echo "Invoking chaincode query on all org2 nodes"
export CORE_PEER_LOCALMSPID="Org2MSP"
export CORE_PEER_MSPCONFIGPATH=$IBC_ORG2_ADMIN_MSP
export CORE_PEER_ADDRESS=$IBC_PEER_ORG2_PEER0
peer chaincode query -C $CHANNEL_NAME -n fabcar -c '{"Args":["queryCar","a"]}'
export CORE_PEER_ADDRESS=$IBC_PEER_ORG2_PEER1
peer chaincode query -C $CHANNEL_NAME -n fabcar -c '{"Args":["queryCar","a"]}'
export CORE_PEER_ADDRESS=$IBC_PEER_ORG2_PEER2
peer chaincode query -C $CHANNEL_NAME -n fabcar -c '{"Args":["queryCar","a"]}'

cd $CURR_PWD