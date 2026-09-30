# NetMind Terraform Infrastructure
# Defines VPC, EKS Cluster, and RDS Database for realistic deployment.

provider "aws" {
  region = var.aws_region
}

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = "netmind-vpc"
  cidr = "10.0.0.0/16"

  azs             = ["us-west-2a", "us-west-2b", "us-west-2c"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]

  enable_nat_gateway = true
  single_nat_gateway = true
}

module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.0"

  cluster_name    = "netmind-cluster"
  cluster_version = "1.30"
  
  vpc_id                   = module.vpc.vpc_id
  subnet_ids               = module.vpc.private_subnets
  control_plane_subnet_ids = module.vpc.public_subnets

  eks_managed_node_groups = {
    general = {
      instance_types = ["t3.large"]
      min_size     = 2
      max_size     = 5
      desired_size = 3
    }
  }
}

module "db" {
  source  = "terraform-aws-modules/rds/aws"
  version = "~> 6.0"

  identifier = "netmind-postgres"
  engine     = "postgres"
  engine_version = "15"
  instance_class = "db.t3.medium"
  allocated_storage = 50

  db_name  = "netmind"
  username = "netmind_admin"
  password = var.db_password
  port     = 5432

  vpc_security_group_ids = [module.vpc.default_security_group_id]
  subnet_ids             = module.vpc.private_subnets
}

resource "aws_s3_bucket" "mlflow_artifacts" {
  bucket = "netmind-mlflow-artifacts-${var.environment}"
}
