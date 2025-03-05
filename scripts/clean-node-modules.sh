#!/bin/bash

echo "Cleaning node_modules in server directory..."
rm -rf src/server/node_modules

echo "Reinstalling server dependencies..."
cd src/server
npm ci

echo "Done! Node modules have been reinstalled." 