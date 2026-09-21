import React from 'react';

export interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  className?: string;
  variant?: 'rectangular' | 'circular' | 'text';
  width?: string | number;
  height?: string | number;
}

export const Skeleton: React.FC<SkeletonProps> = ({
  className = '',
  variant = 'rectangular',
  width,
  height,
  style,
  ...rest
}) => {
  const roundedClass = {
    rectangular: 'rounded-lg',
    circular: 'rounded-full',
    text: 'rounded-md',
  }[variant];

  return (
    <div
      className={`animate-pulse bg-slate-800/60 ${roundedClass} ${className}`}
      style={{
        width,
        height: height || (variant === 'text' ? '1rem' : undefined),
        ...style,
      }}
      aria-hidden="true"
      {...rest}
    />
  );
};

export const CardSkeleton: React.FC<{ rows?: number }> = ({ rows = 3 }) => {
  return (
    <div
      className="rounded-xl border border-slate-800 bg-slate-900/80 p-5 shadow-sm space-y-3"
      style={{ backgroundColor: '#111927', borderColor: '#1e293b' }}
    >
      <Skeleton width="40%" height="0.875rem" variant="text" />
      <Skeleton width="70%" height="1.75rem" variant="text" />
      {rows > 2 && <Skeleton width="50%" height="0.75rem" variant="text" />}
    </div>
  );
};
