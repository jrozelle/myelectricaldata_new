import { useState, useRef, useEffect, ReactNode } from 'react'
import { Info } from 'lucide-react'

interface TooltipProps {
  content: string | ReactNode
  children: ReactNode
  placement?: 'top' | 'bottom' | 'left' | 'right'
  delay?: number
  showArrow?: boolean
  maxWidth?: string
  trigger?: 'hover' | 'click'
}

export function Tooltip({
  content,
  children,
  placement = 'top',
  delay = 200,
  showArrow = true,
  maxWidth = '16rem',
  trigger = 'hover',
}: TooltipProps) {
  const [isVisible, setIsVisible] = useState(false)
  const [position, setPosition] = useState({ top: 0, left: 0 })
  const triggerRef = useRef<HTMLDivElement>(null)
  const tooltipRef = useRef<HTMLDivElement>(null)
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const showTooltip = () => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current)
    }
    timeoutRef.current = setTimeout(() => {
      setIsVisible(true)
    }, delay)
  }

  const hideTooltip = () => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current)
    }
    setIsVisible(false)
  }

  const toggleTooltip = () => {
    if (isVisible) {
      hideTooltip()
    } else {
      setIsVisible(true)
    }
  }

  useEffect(() => {
    if (!isVisible || !triggerRef.current || !tooltipRef.current) return

    const updatePosition = () => {
      if (!triggerRef.current || !tooltipRef.current) return

      const triggerRect = triggerRef.current.getBoundingClientRect()
      const tooltipRect = tooltipRef.current.getBoundingClientRect()

      let top = 0
      let left = 0

      const spacing = showArrow ? 12 : 8

      switch (placement) {
        case 'top':
          top = triggerRect.top - tooltipRect.height - spacing
          left = triggerRect.left + (triggerRect.width - tooltipRect.width) / 2
          break
        case 'bottom':
          top = triggerRect.bottom + spacing
          left = triggerRect.left + (triggerRect.width - tooltipRect.width) / 2
          break
        case 'left':
          top = triggerRect.top + (triggerRect.height - tooltipRect.height) / 2
          left = triggerRect.left - tooltipRect.width - spacing
          break
        case 'right':
          top = triggerRect.top + (triggerRect.height - tooltipRect.height) / 2
          left = triggerRect.right + spacing
          break
      }

      // Keep tooltip within viewport
      const padding = 8
      top = Math.max(padding, Math.min(top, window.innerHeight - tooltipRect.height - padding))
      left = Math.max(padding, Math.min(left, window.innerWidth - tooltipRect.width - padding))

      setPosition({ top, left })
    }

    updatePosition()
    window.addEventListener('scroll', updatePosition, true)
    window.addEventListener('resize', updatePosition)

    return () => {
      window.removeEventListener('scroll', updatePosition, true)
      window.removeEventListener('resize', updatePosition)
    }
  }, [isVisible, placement, showArrow])

  useEffect(() => {
    if (trigger === 'click' && isVisible) {
      const handleClickOutside = (event: MouseEvent) => {
        if (
          tooltipRef.current &&
          triggerRef.current &&
          !tooltipRef.current.contains(event.target as Node) &&
          !triggerRef.current.contains(event.target as Node)
        ) {
          hideTooltip()
        }
      }

      document.addEventListener('mousedown', handleClickOutside)
      return () => document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [isVisible, trigger])

  const arrowClasses = {
    top: 'left-1/2 -translate-x-1/2 bottom-[-4px] border-l-transparent border-r-transparent border-b-transparent',
    bottom: 'left-1/2 -translate-x-1/2 top-[-4px] border-l-transparent border-r-transparent border-t-transparent',
    left: 'top-1/2 -translate-y-1/2 right-[-4px] border-t-transparent border-b-transparent border-r-transparent',
    right: 'top-1/2 -translate-y-1/2 left-[-4px] border-t-transparent border-b-transparent border-l-transparent',
  }

  return (
    <>
      <div
        ref={triggerRef}
        onMouseEnter={trigger === 'hover' ? showTooltip : undefined}
        onMouseLeave={trigger === 'hover' ? hideTooltip : undefined}
        onClick={trigger === 'click' ? toggleTooltip : undefined}
        className="inline-flex"
      >
        {children}
      </div>

      {isVisible && (
        <div
          ref={tooltipRef}
          className="fixed z-50 px-3 py-2 text-sm text-white bg-gray-900 dark:bg-gray-700 rounded-lg shadow-lg animate-in fade-in zoom-in-95 duration-150"
          style={{
            top: `${position.top}px`,
            left: `${position.left}px`,
            maxWidth,
          }}
          role="tooltip"
        >
          {content}
          {showArrow && (
            <div
              className={`absolute w-2 h-2 bg-gray-900 dark:bg-gray-700 rotate-45 ${arrowClasses[placement]}`}
              aria-hidden="true"
            />
          )}
        </div>
      )}
    </>
  )
}

interface InfoTooltipProps {
  content: string | ReactNode
  placement?: 'top' | 'bottom' | 'left' | 'right'
  size?: number
}

export function InfoTooltip({ content, placement = 'top', size = 16 }: InfoTooltipProps) {
  return (
    <Tooltip content={content} placement={placement}>
      <button
        type="button"
        className="inline-flex items-center justify-center text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
        aria-label="Plus d'informations"
      >
        <Info size={size} />
      </button>
    </Tooltip>
  )
}
