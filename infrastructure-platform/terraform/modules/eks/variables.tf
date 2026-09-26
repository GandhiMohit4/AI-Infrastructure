variable "cluster_name" {
  description = "EKS cluster name"
  type        = string
}

variable "kubernetes_version" {
  description = "Kubernetes version"
  type        = string
}

variable "cluster_role_arn" {
  description = "IAM role ARN for EKS cluster"
  type        = string
}

variable "subnet_ids" {
  description = "Subnets used by EKS"
  type        = list(string)
}

variable "cluster_role_policy_attachment" {
  description = "Dependency for EKS cluster IAM policy"
  type        = any
}

variable "tags" {
  type    = map(string)
  default = {}
}