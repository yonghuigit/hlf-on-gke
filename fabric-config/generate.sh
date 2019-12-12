#!/bin/bash

CURR_PWD=$PWD
BASEDIR=$(dirname "$0")
source $BASEDIR/setvars.sh

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

if [ -z ${SYS_CHANNEL_NAME+x} ]; then
  echo "SYS_CHANNEL_NAME is not set, exiting"
  exit 1;
elif [ -z ${ORDERER_ORG_DOMAIN+x} ]; then
  echo "ORDERER_ORG_DOMAIN is not set, exiting"
  exit 1;
elif [ -z ${ORG1_DOMAIN+x} ]; then
  echo "ORG1_DOMAIN is not set, exiting"
  exit 1;
elif [ -z ${ORG2_DOMAIN+x} ]; then
  echo "ORG2_DOMAIN is not set, exiting"
  exit 1;
fi

if [ -d "$BASEDIR/crypto-config" ]; then
  echo "***We will remove previously generated crypto and configuration materials and start from scratch***" 
  askProceed
fi

cd $BASEDIR
rm -rf crypto-config
rm -rf channel-artifacts
mkdir channel-artifacts

rm -rf ../hlf-network/crypto-config
rm -rf ../hlf-network/crypto-config.yaml
rm -rf ../hlf-network/channel-artifacts

echo "Replacing host name tokens in config files"
sed -i -e s/_ORDERER_ORG_DOMAIN_/$ORDERER_ORG_DOMAIN/g *.yaml
sed -i -e s/_ORG1_DOMAIN_/$ORG1_DOMAIN/g *.yaml
sed -i -e s/_ORG2_DOMAIN_/$ORG2_DOMAIN/g *.yaml

rm -f *-e

echo "Generating crypto materials..."
cryptogen generate --config=./crypto-config.yaml 

echo "Generating genesis block..."
configtxgen -profile SampleMultiNodeEtcdRaft -channelID $SYS_CHANNEL_NAME -outputBlock ./channel-artifacts/genesis.block

echo "Copying generated materials into helm chart: hlf-network"
cp -r crypto-config ../hlf-network
cp -r channel-artifacts ../hlf-network
cp crypto-config.yaml ../hlf-network

cd $CURR_PWD
