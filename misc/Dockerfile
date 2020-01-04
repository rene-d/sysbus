FROM golang:alpine as builder
COPY proxy.go /go
RUN env CGO_ENABLED=0 go build proxy.go

FROM scratch
VOLUME /out
COPY --from=builder /go/proxy /
CMD [ "/proxy", "/out/livebox.log" ]
