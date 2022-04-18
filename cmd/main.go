package main

import (
	"fmt"
	"net/http"

	"github.com/omertuc/assisted-swarm/restapi"
	"github.com/omertuc/assisted-swarm/src/api"
	"github.com/openshift/assisted-installer-agent/src/util"
	"github.com/sirupsen/logrus"
)

const (
	ListenPort      = 5566
	MainDummyHostID = "ffffffff-ffff-ffff-ffff-ffffffffffff"
)

func main() {
	util.SetLogging("combined-agent", false, true, MainDummyHostID)
	failOnError := func(err error, msg string, args ...interface{}) {
		if err != nil {
			logrus.WithError(err).Fatalf(msg, args...)
		}
	}
	h, err := restapi.Handler(restapi.Config{
		SwarmAPI: &api.SwarmAPI{},
		Logger:   logrus.Printf,
	})
	failOnError(err, "Create handler")
	logrus.Fatal(http.ListenAndServe(fmt.Sprintf("127.0.0.1:%d", ListenPort), h))
}
