variable "project_id" { type = string }
variable "region" { type = string }
variable "app_name" { type = string }
variable "environment" { type = string }
variable "container_image" { type = string }
variable "service_account_email" { type = string }
variable "min_instances" { type = number; default = 1 }
variable "max_instances" { type = number; default = 10 }
variable "memory" { type = string; default = "2Gi" }
variable "cpu" { type = string; default = "2" }
variable "labels" { type = map(string); default = {} }
variable "env_vars" { type = map(string); default = {} }
