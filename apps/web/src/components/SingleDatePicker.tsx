import { useState, useRef, useEffect } from 'react'
import { format } from 'date-fns'
import { fr } from 'date-fns/locale'
import { DayPicker } from 'react-day-picker'
import { Calendar } from 'lucide-react'
import 'react-day-picker/style.css'

// Locale française avec mois en majuscule
const frCapitalized = {
  ...fr,
  localize: {
    ...fr.localize,
    month: (n: number) => {
      const months = [
        'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
        'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre'
      ]
      return months[n]
    }
  }
}

interface SingleDatePickerProps {
  value: string // Format YYYY-MM-DD
  onChange: (date: string) => void
  disabled?: boolean
  minDate?: string
  maxDate?: string
  label?: string
  required?: boolean
  className?: string
}

export function SingleDatePicker({
  value,
  onChange,
  disabled,
  minDate,
  maxDate,
  label,
  required,
  className = ''
}: SingleDatePickerProps) {
  const [isOpen, setIsOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

  // Fermer au clic extérieur
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleSelect = (date: Date | undefined) => {
    if (date) {
      onChange(format(date, 'yyyy-MM-dd'))
      setIsOpen(false)
    }
  }

  // Formater la date pour l'affichage
  const formatDateLong = (dateStr: string) => {
    if (!dateStr) return 'Sélectionner une date'
    const date = new Date(dateStr)
    return date.toLocaleDateString('fr-FR', {
      weekday: 'long',
      day: 'numeric',
      month: 'long',
      year: 'numeric'
    })
  }

  // Date max par défaut : aujourd'hui + 1 an
  const defaultMaxDate = new Date()
  defaultMaxDate.setFullYear(defaultMaxDate.getFullYear() + 1)

  const pickerStyles = `
    .single-date-picker-container {
      --rdp-accent-color: #3b82f6 !important;
      --rdp-accent-background-color: #3b82f6 !important;
      --rdp-selected-color: #ffffff !important;
      --rdp-selected-border: 2px solid #3b82f6 !important;
    }
    .single-date-picker-container .rdp-today:not(.rdp-selected) .rdp-day_button {
      border: 2px solid #3b82f6 !important;
      border-radius: 9999px;
    }
    .single-date-picker-container .rdp-selected .rdp-day_button {
      border: 2px solid #3b82f6 !important;
    }
    .single-date-picker-container .rdp-chevron {
      fill: #3b82f6 !important;
    }
    .dark .single-date-picker-container {
      --rdp-accent-color: #60a5fa !important;
      --rdp-accent-background-color: #3b82f6 !important;
      --rdp-selected-border: 2px solid #60a5fa !important;
      --rdp-day-color: #f3f4f6;
      --rdp-month-caption-color: #f3f4f6;
      --rdp-weekday-color: #9ca3af;
      --rdp-outside-color: #6b7280;
      --rdp-disabled-color: #4b5563;
      --rdp-selected-color: #ffffff !important;
    }
    .dark .single-date-picker-container .rdp-today:not(.rdp-selected) .rdp-day_button {
      border: 2px solid #60a5fa !important;
      border-radius: 9999px;
    }
    .dark .single-date-picker-container .rdp-selected .rdp-day_button {
      border: 2px solid #60a5fa !important;
    }
    .dark .single-date-picker-container .rdp-chevron {
      fill: #60a5fa !important;
    }
    .dark .single-date-picker-container button:hover:not([disabled]) {
      background-color: #374151;
    }
    /* Caption layout - dropdowns centered */
    .single-date-picker-container .rdp-month_caption {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 1.5rem;
      margin-bottom: 0.75rem;
    }
    .single-date-picker-container .rdp-dropdowns {
      display: flex;
      align-items: center;
      gap: 1.5rem;
    }
    /* Hide navigation */
    .single-date-picker-container .rdp-nav,
    .single-date-picker-container .rdp-button_previous,
    .single-date-picker-container .rdp-button_next {
      display: none !important;
    }
    .single-date-picker-container .rdp-dropdown,
    .single-date-picker-container .rdp-dropdowns select,
    .single-date-picker-container select.rdp-dropdown {
      -webkit-appearance: none;
      -moz-appearance: none;
      appearance: none;
      padding: 0.375rem 2.5rem 0.375rem 0.75rem;
      border-radius: 0.5rem;
      border: 1px solid #d1d5db;
      background-color: white;
      font-size: 0.875rem;
      font-weight: 500;
      cursor: pointer;
      text-transform: capitalize;
      background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%236b7280'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='M19 9l-7 7-7-7'%3E%3C/path%3E%3C/svg%3E");
      background-repeat: no-repeat;
      background-position: right 0.75rem center;
      background-size: 1rem;
      box-sizing: border-box;
    }
    /* Month dropdown */
    .single-date-picker-container .rdp-months_dropdown,
    .single-date-picker-container .rdp-dropdown_months,
    .single-date-picker-container select[name="months"],
    .single-date-picker-container .rdp-dropdowns select:first-of-type,
    .single-date-picker-container .rdp-dropdowns > *:first-child,
    .single-date-picker-container .rdp-dropdowns > *:first-child select {
      width: 140px !important;
      min-width: 140px !important;
      max-width: 140px !important;
      box-sizing: border-box !important;
    }
    /* Year dropdown */
    .single-date-picker-container .rdp-years_dropdown,
    .single-date-picker-container .rdp-dropdown_years,
    .single-date-picker-container select[name="years"],
    .single-date-picker-container .rdp-dropdowns select:last-of-type,
    .single-date-picker-container .rdp-dropdowns > *:last-child,
    .single-date-picker-container .rdp-dropdowns > *:last-child select {
      width: 90px !important;
      min-width: 90px !important;
      max-width: 90px !important;
      box-sizing: border-box !important;
      text-align: left;
      text-align-last: left;
    }
    /* Focus styles */
    .single-date-picker-container .rdp-dropdown:focus,
    .single-date-picker-container .rdp-dropdowns select:focus,
    .single-date-picker-container select.rdp-dropdown:focus,
    .single-date-picker-container select:focus {
      outline: 0 !important;
      box-shadow: none !important;
      border: 1px solid #3b82f6 !important;
    }
    .single-date-picker-container *:focus {
      outline: none !important;
    }
    .dark .single-date-picker-container .rdp-dropdown,
    .dark .single-date-picker-container .rdp-dropdowns select,
    .dark .single-date-picker-container select.rdp-dropdown {
      background-color: #374151;
      border-color: #4b5563;
      color: #f3f4f6;
      background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%239ca3af'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='M19 9l-7 7-7-7'%3E%3C/path%3E%3C/svg%3E");
    }
    .dark .single-date-picker-container .rdp-dropdown:focus,
    .dark .single-date-picker-container select:focus {
      border-color: #60a5fa !important;
    }
    .dark .single-date-picker-container .rdp-dropdown option {
      background-color: #374151;
      color: #f3f4f6;
    }
    .single-date-picker-container .rdp-dropdown option,
    .single-date-picker-container .rdp-dropdown_months option {
      text-transform: capitalize;
    }
    .single-date-picker-container .rdp-month_caption {
      text-transform: capitalize;
    }
  `

  return (
    <div ref={containerRef} className={`relative ${className}`}>
      <style>{pickerStyles}</style>

      {label && (
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          {label}
          {required && <span className="text-red-500 ml-1">*</span>}
        </label>
      )}

      {/* Bouton de sélection */}
      <button
        type="button"
        onClick={() => !disabled && setIsOpen(!isOpen)}
        disabled={disabled}
        className={`
          flex items-center gap-3 px-4 py-3 rounded-xl border-2
          ${isOpen
            ? 'border-primary-500 ring-2 ring-primary-500/20'
            : 'border-primary-300 dark:border-primary-700 hover:border-primary-400 dark:hover:border-primary-600'
          }
          bg-white dark:bg-gray-800
          text-gray-900 dark:text-white font-medium
          focus:outline-none transition-all duration-200
          ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
          text-sm
        `}
      >
        <Calendar className="text-primary-600 dark:text-primary-400 flex-shrink-0" size={20} />
        <span className="capitalize">{formatDateLong(value)}</span>
      </button>

      {/* Popup calendrier */}
      {isOpen && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setIsOpen(false)} />
          <div className="absolute left-0 z-50 mt-2 bg-white dark:bg-gray-800 rounded-xl shadow-2xl border-2 border-primary-300 dark:border-primary-700 p-4">
            <div className="single-date-picker-container">
              <DayPicker
                mode="single"
                captionLayout="dropdown"
                startMonth={minDate ? new Date(minDate) : new Date(2020, 0)}
                endMonth={maxDate ? new Date(maxDate) : defaultMaxDate}
                selected={value ? new Date(value) : undefined}
                onSelect={handleSelect}
                locale={frCapitalized}
                disabled={[
                  ...(minDate ? [{ before: new Date(minDate) }] : []),
                  ...(maxDate ? [{ after: new Date(maxDate) }] : [])
                ]}
                defaultMonth={value ? new Date(value) : new Date()}
              />
            </div>
          </div>
        </>
      )}
    </div>
  )
}
