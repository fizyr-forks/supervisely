FROM supervisely/base-py-sdk:6.66.4

ARG tag_ref_name

RUN pip install ruamel.yaml==0.17.21
RUN pip install --upgrade supervisely==$tag_ref_name
RUN pip install --upgrade supervisely[apps]==$tag_ref_name
RUN pip install --upgrade supervisely[aug]==${tag_ref_name}
