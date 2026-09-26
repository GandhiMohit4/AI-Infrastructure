variable "cluster_name" {
  type = string
}

variable "node_group_name" {
  type = string
}

variable "node_role_arn" {
  type = string
}

variable "subnet_ids" {
  type = list(string)
}

variable "instance_types" {
  type = list(string)
}

variable "capacity_type" {
  type    = string
  default = "ON_DEMAND"

  validation {
    condition = contains(
      ["ON_DEMAND", "SPOT"],
      var.capacity_type
    )

    error_message = "capacity_type must be ON_DEMAND or SPOT."
  }
}

variable "ami_type" {
  type    = string
  default = "AL2023_x86_64_STANDARD"
}

variable "disk_size" {
  type    = number
  default = 50
}

variable "desired_size" {
  type = number
}

variable "min_size" {
  type = number
}

variable "max_size" {
  type = number
}

variable "labels" {
  type    = map(string)
  default = {}
}

variable "taints" {
  type = list(object({
    key    = string
    value  = string
    effect = string
  }))

  default = []
}

variable "tags" {
  type    = map(string)
  default = {}
}
