#!/bin/bash

CURR_PWD=$PWD
BASEDIR=$(dirname "$0")
CHANNEL_NAME=mychannel

# Ask user for confirmation to proceed
function askProceed() {
  read -p "Continue? [Y/n] " ans
  case "$ans" in
  y | Y | "")
    echo "OK, proceeding ..."
    ;;
  n | N)
    echo "OK, nothing will be regenerated, exiting..."
    exit 1
    ;;
  *)
    echo "invalid response"
    askProceed
    ;;
  esac
}

if [ -d "$BASEDIR/crypto-config" ]; then
  echo "***We will remove previously generated crypto and configuration materials and start from scratch***" 
  askProceed
fi

cd $BASEDIR
rm -rf crypto-config
rm -rf channel-artifacts
rm -rf ../hlf-network/crypto-config
rm -rf ../hlf-network/crypto-config.yaml
rm -rf ../hlf-network/channel-artifacts
mkdir channel-artifacts

echo "Generating crypto materials..."
cryptogen generate --config=./crypto-config.yaml 
echo "Generating genesis block..."
configtxgen -profile SampleMultiNodeEtcdRaft -channelID byfn-sys-channel -outputBlock ./channel-artifacts/genesis.block
echo "Generating channel related configurations"
configtxgen -profile TwoOrgsChannel -outputCreateChannelTx ./channel-artifacts/channel.tx -channelID $CHANNEL_NAME
configtxgen -profile TwoOrgsChannel -outputAnchorPeersUpdate ./channel-artifacts/Org1MSPanchors.tx -channelID $CHANNEL_NAME -asOrg Org1MSP
configtxgen -profile TwoOrgsChannel -outputAnchorPeersUpdate ./channel-artifacts/Org2MSPanchors.tx -channelID $CHANNEL_NAME -asOrg Org2MSP
echo "Copying generated materials into helm chart: hlf-network"
cp -r crypto-config ../hlf-network
cp -r channel-artifacts ../hlf-network
cp crypto-config.yaml ../hlf-network

cd $CURR_PWD
