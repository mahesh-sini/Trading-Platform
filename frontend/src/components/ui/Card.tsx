import React from 'react';
import { clsx } from 'clsx';
import { BaseComponentProps } from '@/types';

interface CardProps extends BaseComponentProps {
  variant?: 'default' | 'outlined' | 'elevated';
  padding?: 'none' | 'sm' | 'md' | 'lg';
}

export const Card: React.FC<CardProps> = ({
  children,
  className,
  variant = 'default',
  padding = 'md',
}) => {
  const baseStyles = 'bg-white rounded-lg';
  
  const variantStyles = {
    default: 'border border-gray-200',
    outlined: 'border-2 border-gray-300',
    elevated: 'shadow-custom-lg border border-gray-100',
  };
  
  const paddingStyles = {
    none: '',
    sm: 'p-4',
    md: 'p-6',
    lg: 'p-8',
  };
  
  return (
    <div
      className={clsx(
        baseStyles,
        variantStyles[variant],
        paddingStyles[padding],
        className
      )}
    >
      {children}
    </div>
  );
};

interface CardHeaderProps extends BaseComponentProps {
  title?: string;
  subtitle?: string;
}

export const CardHeader: React.FC<CardHeaderProps> = ({
  children,
  className,
  title,
  subtitle,
}) => {
  return (
    <div className={clsx('mb-4', className)}>
      {title && (
        <h3 className="text-lg font-semibold text-gray-900 mb-1">{title}</h3>
      )}
      {subtitle && (
        <p className="text-sm text-gray-600 mb-2">{subtitle}</p>
      )}
      {children}
    </div>
  );
};

interface CardBodyProps extends BaseComponentProps {}

export const CardBody: React.FC<CardBodyProps> = ({ children, className }) => {
  return <div className={clsx('', className)}>{children}</div>;
};

interface CardFooterProps extends BaseComponentProps {}

export const CardFooter: React.FC<CardFooterProps> = ({ children, className }) => {
  return (
    <div className={clsx('mt-4 pt-4 border-t border-gray-200', className)}>
      {children}
    </div>
  );
};