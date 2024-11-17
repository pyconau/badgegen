FROM rust:1.82-alpine as svg2pdf-cli
RUN apk add musl-dev
RUN cargo install svg2pdf-cli

FROM python:3.13-alpine as runtime
RUN apk add fontconfig
RUN pip install poetry==1.8.4
VOLUME ["/src", "/run"]
WORKDIR /src
COPY ./badgegen /src/badgegen
COPY ./poetry.lock /src/poetry.lock
COPY ./pyproject.toml /src/pyproject.toml
COPY ./find_by_name /src/find_by_name

RUN mkdir -p /run/output/svgs /run/output/pdfs
RUN touch /run/output/svgs/debug /run/output/pdfs/debug

COPY --from=svg2pdf-cli /usr/local/cargo/bin/svg2pdf /usr/local/cargo/bin/svg2pdf
COPY --from=svg2pdf-cli /usr/local/cargo/bin/svg2pdf /bin/svg2pdf

RUN poetry install

WORKDIR /run

ENV PRETIX_TOKEN=

# ENV PATH "$PATH:/bin"

ENTRYPOINT ["poetry", "-C", "/src/", "run", "python", "/src/badgegen/badgegen.py"]

