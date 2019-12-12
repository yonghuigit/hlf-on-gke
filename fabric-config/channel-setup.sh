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
echo "FABRIC_CFG_PATH is set to $FABRIC_CFG_PATH"

cd $BASEDIR

echo "Replacing host name tokens in config files"
sed -i -e s/_ORDERER_ORG_DOMAIN_/$ORDERER_ORG_DOMAIN/g *.yaml
sed -i -e s/_ORG1_DOMAIN_/$ORG1_DOMAIN/g *.yaml
sed -i -e s/_ORG2_DOMAIN_/$ORG2_DOMAIN/g *.yaml
rm -f *-e

echo "Generating channel related configurations"
configtxgen -profile TwoOrgsChannel -outputCreateChannelTx ./channel-artifacts/${CHANNEL_NAME}_channel.tx -channelID $CHANNEL_NAME
configtxgen -profile TwoOrgsChannel -outputAnchorPeersUpdate ./channel-artifacts/${CHANNEL_NAME}_Org1MSPanchors.tx -channelID $CHANNEL_NAME -asOrg Org1MSP
configtxgen -profile TwoOrgsChannel -outputAnchorPeersUpdate ./channel-artifacts/${CHANNEL_NAME}_Org2MSPanchors.tx -channelID $CHANNEL_NAME -asOrg Org2MSP

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


export CORE_PEER_LOCALMSPID="Org1MSP"
export CORE_PEER_MSPCONFIGPATH=$IBC_ORG1_ADMIN_MSP
export CORE_PEER_ADDRESS=$IBC_PEER_ORG1_PEER0

peer channel create -o $IBC_ORDERER_END_POINT -c $CHANNEL_NAME -f ./channel-artifacts/${CHANNEL_NAME}_channel.tx --tls --cafile=$CORE_PEER_TLS_ROOTCERT_FILE
peer channel join -b $CHANNEL_NAME.block

export CORE_PEER_ADDRESS=$IBC_PEER_ORG1_PEER1
peer channel join -b $CHANNEL_NAME.block

export CORE_PEER_ADDRESS=$IBC_PEER_ORG1_PEER2
peer channel join -b $CHANNEL_NAME.block

peer channel update -o $IBC_ORDERER_END_POINT -c $CHANNEL_NAME -f ./channel-artifacts/${CHANNEL_NAME}_Org1MSPanchors.tx --tls --cafile=$CORE_PEER_TLS_ROOTCERT_FILE

export CORE_PEER_LOCALMSPID="Org2MSP"
export CORE_PEER_MSPCONFIGPATH=$IBC_ORG2_ADMIN_MSP
export CORE_PEER_ADDRESS=$IBC_PEER_ORG2_PEER0

peer channel join -b $CHANNEL_NAME.block

export CORE_PEER_ADDRESS=$IBC_PEER_ORG2_PEER1
peer channel join -b $CHANNEL_NAME.block

export CORE_PEER_ADDRESS=$IBC_PEER_ORG2_PEER2
peer channel join -b $CHANNEL_NAME.block

peer channel update -o $IBC_ORDERER_END_POINT -c $CHANNEL_NAME -f ./channel-artifacts/${CHANNEL_NAME}_Org2MSPanchors.tx --tls --cafile=$CORE_PEER_TLS_ROOTCERT_FILE

cd $CURR_PWD
