FROM fserena/python-base
LABEL maintainer=kudhmud@gmail.com

RUN /root/.env/bin/pip install -U pip
RUN /root/.env/bin/pip install --upgrade git+https://github.com/fserena/agora-py.git
RUN /root/.env/bin/pip install --upgrade git+https://github.com/fserena/agora-wot.git
RUN /root/.env/bin/pip install --upgrade git+https://github.com/fserena/agora-gw.git
RUN /root/.env/bin/pip install --upgrade git+https://github.com/fserena/agora-graphql.git
