import React from 'react'

interface LogoProps {
  variant?: 'full' | 'icon' | 'horizontal'
  size?: number | 'sm' | 'md' | 'lg' | 'xl'
  theme?: 'light' | 'dark'
  className?: string
  style?: React.CSSProperties
}

export const LogoIcon: React.FC<{ size?: number; className?: string; style?: React.CSSProperties }> = ({
  size = 36,
  className,
  style,
}) => {
  return (
    <img
      src="/logo-icon.png"
      alt="DualTrust AI Emblem"
      className={className}
      style={{
        width: size,
        height: size,
        objectFit: 'contain',
        display: 'inline-block',
        verticalAlign: 'middle',
        ...style,
      }}
    />
  )
}

export const DualTrustLogo: React.FC<LogoProps> = ({
  variant = 'full',
  size = 'md',
  theme = 'light',
  className,
  style,
}) => {
  const pixelSizes = {
    sm: { imgWidth: 140, iconSize: 24, fontSize: 14 },
    md: { imgWidth: 200, iconSize: 34, fontSize: 18 },
    lg: { imgWidth: 260, iconSize: 44, fontSize: 24 },
    xl: { imgWidth: 320, iconSize: 56, fontSize: 30 },
  }

  const currentSize = typeof size === 'number' 
    ? { imgWidth: size * 3, iconSize: size, fontSize: size * 0.55 }
    : pixelSizes[size] || pixelSizes.md

  if (variant === 'icon') {
    return <LogoIcon size={currentSize.iconSize} className={className} style={style} />
  }

  if (variant === 'horizontal') {
    const textColor = theme === 'dark' ? '#f8fafc' : '#0e3775'
    return (
      <div
        className={className}
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: Math.round(currentSize.iconSize * 0.28),
          lineHeight: 1,
          ...style,
        }}
      >
        <LogoIcon size={currentSize.iconSize} />
        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <span
            style={{
              fontFamily: "'Inter', sans-serif",
              fontWeight: 800,
              fontSize: currentSize.fontSize,
              color: textColor,
              letterSpacing: '-0.02em',
            }}
          >
            DUALTRUST
          </span>
          <span
            style={{
              fontFamily: "'Inter', sans-serif",
              fontWeight: 800,
              fontSize: currentSize.fontSize,
              color: '#f79f1a',
              letterSpacing: '-0.02em',
            }}
          >
            AI
          </span>
        </div>
      </div>
    )
  }

  // Full stacked logo (Emblem on top, DUALTRUST AI below)
  return (
    <img
      src="/logo.png"
      alt="DualTrust AI"
      className={className}
      style={{
        width: currentSize.imgWidth,
        height: 'auto',
        objectFit: 'contain',
        display: 'block',
        ...style,
      }}
    />
  )
}

export default DualTrustLogo
