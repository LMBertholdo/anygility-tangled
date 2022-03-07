job "verfploeter" {
  datacenters = ["dc1"]
  type = "system"
  group "anycast" {
    restart {
      attempts = 5
      delay = "10s"
      interval = "2m"
      mode = "delay"
    }
    task "server" {
    constraint {
      attribute = "${node.class}"
      value = "anycast"
    }
    env {
        "RUST_LOG" = "verfploeter"
    }
      artifact {
        source = "https://github.com/LMBertholdo/verfploeter/releases/download/v0.1.42/verfploeter"
      }
      driver = "raw_exec"
      config {
        command = "verfploeter"
        args = ["--prometheus", "0.0.0.0:9090", "client", "-h", "${node.unique.name}", "-s", "anycast-master-vpn:50001"]
      }
    }
  }
  group "master" {
    task "server" {
    constraint {
      attribute = "${node.class}"
      value = "master"
    }
    env {
        "RUST_LOG" = "debug"
    }
      artifact {
        source = "https://github.com/LMBertholdo/verfploeter/releases/download/v0.1.42/verfploeter"
      }
      driver = "raw_exec"
      config {
        command = "verfploeter"
        args = ["server"]
      }
    }
  }
}
