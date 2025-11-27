import { useEffect, useState } from 'react'

interface PageTransitionProps {
  children: React.ReactNode
}

/**
 * Composant qui ajoute des transitions fluides entre les pages.
 * Utilise un effet de fade + slide subtil lors du montage.
 * Le composant doit recevoir une key={pathname} pour déclencher l'animation à chaque navigation.
 */
export function PageTransition({ children }: PageTransitionProps) {
  const [isVisible, setIsVisible] = useState(false)

  useEffect(() => {
    // Scroll vers le haut
    window.scrollTo({ top: 0, behavior: 'smooth' })

    // Déclencher l'animation d'entrée après le montage
    const timer = requestAnimationFrame(() => {
      setIsVisible(true)
    })

    return () => cancelAnimationFrame(timer)
  }, [])

  return (
    <div
      className={`transition-all duration-300 ease-out ${
        isVisible
          ? 'opacity-100 translate-y-0 scale-100'
          : 'opacity-0 translate-y-3 scale-[0.98]'
      }`}
      style={{
        transformOrigin: 'top center',
        willChange: isVisible ? 'auto' : 'opacity, transform'
      }}
    >
      {children}
    </div>
  )
}
