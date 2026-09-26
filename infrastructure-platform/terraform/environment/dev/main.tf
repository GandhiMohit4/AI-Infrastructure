terraform {
  required_version = ">= 1.9.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }

  backend "s3" {
    bucket       = "ai-platform-terraform-state-mohit"
    key          = "environments/dev/terraform.tfstate"
    region       = "us-east-1"
    use_lockfile = true
    encrypt      = true
  }
}

provider "aws" {
  region = "us-east-1"
}

module "vpc" {
  source = "../../modules/vpc"

  name = "ai-platform-dev"

  vpc_cidr = "10.0.0.0/16"

  public_subnet_cidrs = [
    "10.0.1.0/24",
    "10.0.2.0/24"
  ]

  private_subnet_cidrs = [
    "10.0.11.0/24",
    "10.0.12.0/24"
  ]

  tags = {
    Project     = "ai-infrastructure"
    Environment = "dev"
    ManagedBy   = "terraform"
  }
}

module "iam" {
  source = "../../modules/iam"

  name = "ai-platform-dev"

  tags = {
    Project     = "ai-infrastructure"
    Environment = "dev"
    ManagedBy   = "terraform"
  }
}

module "eks" {
  source = "../../modules/eks"

  cluster_name = "ai-platform-dev"

  kubernetes_version = "1.33"

  cluster_role_arn = module.iam.eks_cluster_role_arn

  subnet_ids = module.vpc.private_subnet_ids

  cluster_role_policy_attachment = module.iam.eks_cluster_role_arn

  tags = {
    Project     = "ai-infrastructure"
    Environment = "dev"
    ManagedBy   = "terraform"
  }
}

module "cpu_nodes" {
  source = "../../modules/node-groups"

  cluster_name = module.eks.cluster_name

  node_group_name = "cpu-workers"

  node_role_arn = module.iam.eks_node_role_arn

  subnet_ids = module.vpc.private_subnet_ids

  instance_types = [
    "t3.large"
  ]

  capacity_type = "ON_DEMAND"

  desired_size = 2
  min_size     = 1
  max_size     = 4

  disk_size = 50

  labels = {
    workload = "general"
  }

  tags = {
    Project     = "ai-infrastructure"
    Environment = "dev"
    ManagedBy   = "terraform"
  }

  depends_on = [
    module.eks
  ]
}