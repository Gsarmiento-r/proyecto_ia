variable "project_id" { type = string }
variable "region" { type = string }
variable "app_name" { type = string }
variable "environment" { type = string }
variable "labels" { type = map(string); default = {} }
variable "enable_bigquery" { type = bool; default = true }
variable "enable_document_ai" { type = bool; default = true }
variable "service_account_email" { type = string }
