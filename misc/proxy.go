package main

import (
	"bytes"
	"fmt"
	"io"
	"io/ioutil"
	"log"
	"net/http"
	"net/http/httputil"
	"net/url"
	"os"
	"strings"
)

// liveboxURL is the address of the livebox
var originURL = "http://livebox.home"

// proxyAddress is where the reverse proxy listens to
var proxyAddress = ":8000"

// logfile ...
var logfile *os.File

var logLines map[string]bool

// serveReverseProxy runs the reverse proxy for a given url
func serveReverseProxy(res http.ResponseWriter, req *http.Request) {
	// parse the url
	url, _ := url.Parse(originURL)

	// create the reverse proxy
	proxy := httputil.NewSingleHostReverseProxy(url)

	// Update the headers to allow for SSL redirection
	req.URL.Host = url.Host
	req.URL.Scheme = url.Scheme
	req.Header.Set("X-Forwarded-Host", req.Header.Get("Host"))
	req.Host = url.Host

	// Note that ServeHttp is non blocking and uses a go routine under the hood
	proxy.ServeHTTP(res, req)
}

// drainBody reads all of b to memory and then returns two equivalent
// ReadClosers yielding the same bytes.
//
// It returns an error if the initial slurp of all bytes fails. It does not attempt
// to make the returned ReadClosers have identical error-matching behavior.
func drainBody(b io.ReadCloser) (r1, r2 io.ReadCloser, err error) {
	if b == http.NoBody {
		// No copying needed. Preserve the magic sentinel meaning of NoBody.
		return http.NoBody, http.NoBody, nil
	}
	var buf bytes.Buffer
	if _, err = buf.ReadFrom(b); err != nil {
		return nil, b, err
	}
	if err = b.Close(); err != nil {
		return nil, b, err
	}
	return ioutil.NopCloser(&buf), ioutil.NopCloser(bytes.NewReader(buf.Bytes())), nil
}

// getBody returns the body as a string
func getBody(req *http.Request) string {
	var err error
	save := req.Body

	save, req.Body, err = drainBody(req.Body)
	if err != nil {
		return ""
	}

	var b bytes.Buffer

	chunked := len(req.TransferEncoding) > 0 && req.TransferEncoding[0] == "chunked"

	if req.Body != nil {
		var dest io.Writer = &b
		if chunked {
			dest = httputil.NewChunkedWriter(dest)
		}
		_, err = io.Copy(dest, req.Body)
		if chunked {
			dest.(io.Closer).Close()
			io.WriteString(&b, "\r\n")
		}
	}

	req.Body = save

	return string(b.Bytes())
}

func handleRequestAndRedirect(res http.ResponseWriter, req *http.Request) {

	s := fmt.Sprintln(req.Method, req.RequestURI, getBody(req))

	if logfile != nil {
		fmt.Fprint(logfile, s)
	}

	if strings.Contains(s, "\"events\":") == false {
		// do not print events
		_, seen := logLines[s]
		if seen == false {
			log.Print(s)
			logLines[s] = true
		}
	}

	serveReverseProxy(res, req)
}

func main() {
	var err error

	logLines = map[string]bool{}

	logfileName := "livebox.log"
	if len(os.Args) > 1 {
		logfileName = os.Args[1]
	}
	logfile, err = os.OpenFile(logfileName, os.O_RDWR|os.O_CREATE|os.O_APPEND, 0666)
	if err != nil {
		panic(err)
	}

	log.Println("reverse proxy for", originURL)
	log.Println("listening on", proxyAddress)
	log.Println("logging into", logfileName)
	log.Println("open http://localhost" + proxyAddress + "/ in a web browser")

	http.HandleFunc("/", handleRequestAndRedirect)
	err = http.ListenAndServe(proxyAddress, nil)
	if err != nil {
		panic(err)
	}
}
