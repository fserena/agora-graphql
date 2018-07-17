#!/bin/sh
echo "Starting agora-graphql..."

/root/.env/bin/pip install --upgrade git+https://github.com/fserena/agora-py.git
/root/.env/bin/pip install --upgrade git+https://github.com/fserena/agora-wot.git
/root/.env/bin/pip install --upgrade git+https://github.com/fserena/agora-gw.git
/root/.env/bin/pip install git+https://github.com/fserena/agora-graphql.git
/root/.env/bin/gql &
