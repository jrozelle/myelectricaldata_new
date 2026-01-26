import { Heart, X, Coffee, ExternalLink } from 'lucide-react'

interface DonationModalProps {
  isOpen: boolean
  onClose: () => void
}

export default function DonationModal({ isOpen, onClose }: DonationModalProps) {
  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Overlay */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative bg-white dark:bg-gray-800 rounded-2xl shadow-2xl max-w-xl w-full max-h-[90vh] overflow-y-auto animate-fade-in-up">
        {/* Header */}
        <div className="sticky top-0 bg-gradient-to-r from-pink-500 to-rose-500 p-6 rounded-t-2xl">
          <button
            onClick={onClose}
            className="absolute top-4 right-4 p-2 rounded-full bg-white/20 hover:bg-white/30 transition-colors"
            aria-label="Fermer"
          >
            <X size={20} className="text-white" />
          </button>
          <div className="text-center">
            <Heart size={48} className="mx-auto mb-3 text-white animate-pulse" />
            <h3 className="text-2xl font-bold text-white">Soutenez le projet</h3>
            <p className="text-white/80 mt-2">Choisissez votre méthode de donation</p>
          </div>
        </div>

        {/* Contenu */}
        <div className="p-6 space-y-6">
          {/* Option PayPal */}
          <a
            href="https://www.paypal.com/donate/?business=FY25JLXDYLXAJ&no_recurring=0&currency_code=EUR"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-4 p-4 bg-blue-50 dark:bg-blue-900/20 border-2 border-blue-200 dark:border-blue-700 rounded-xl hover:border-blue-400 dark:hover:border-blue-500 transition-all duration-300 group"
          >
            <div className="bg-white p-3 rounded-xl shadow-md group-hover:shadow-lg transition-shadow flex items-center justify-center w-20 h-20">
              <img src="/Paypal_2014_logo.png" alt="PayPal" className="w-14 h-14 object-contain" />
            </div>
            <div className="flex-1">
              <h4 className="text-lg font-bold text-gray-900 dark:text-white">PayPal</h4>
              <p className="text-sm text-gray-600 dark:text-gray-400">Paiement sécurisé par PayPal</p>
            </div>
            <ExternalLink size={20} className="text-blue-500 dark:text-blue-400" />
          </a>

          {/* Option Buy Me a Coffee */}
          <a
            href="https://buymeacoffee.com/m4dm4rtig4n"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-4 p-4 bg-yellow-50 dark:bg-yellow-900/20 border-2 border-yellow-200 dark:border-yellow-700 rounded-xl hover:border-yellow-400 dark:hover:border-yellow-500 transition-all duration-300 group"
          >
            <div className="bg-[#FFDD00] p-3 rounded-xl shadow-md group-hover:shadow-lg transition-shadow flex items-center justify-center w-20 h-20">
              <img src="/buy_me_coffee.png" alt="Buy Me a Coffee" className="w-14 h-14 object-contain" />
            </div>
            <div className="flex-1">
              <h4 className="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2">
                Buy Me a Coffee
                <Coffee size={18} className="text-yellow-600 dark:text-yellow-400" />
              </h4>
              <p className="text-sm text-gray-600 dark:text-gray-400">Offrez-moi un café</p>
            </div>
            <ExternalLink size={20} className="text-yellow-600 dark:text-yellow-400" />
          </a>

          {/* QR Codes */}
          <div className="pt-6 border-t border-gray-200 dark:border-gray-700">
            <p className="text-center text-sm text-gray-500 dark:text-gray-400 mb-6">
              Ou scannez un QR code avec votre téléphone
            </p>
            <div className="flex justify-center gap-28">
              <div className="text-center">
                <div className="bg-white p-4 rounded-xl shadow-lg inline-block hover:shadow-xl transition-shadow">
                  <img src="/paypal.png" alt="QR PayPal" className="w-36 h-36" />
                </div>
                <p className="mt-3 text-sm font-medium text-gray-700 dark:text-gray-300">PayPal</p>
              </div>
              <div className="text-center">
                <div className="bg-white p-4 rounded-xl shadow-lg inline-block hover:shadow-xl transition-shadow">
                  <img src="/qr-code-coffee.png" alt="QR Buy Me a Coffee" className="w-36 h-36" />
                </div>
                <p className="mt-3 text-sm font-medium text-gray-700 dark:text-gray-300">Buy Me a Coffee</p>
              </div>
            </div>
          </div>

          {/* Message de remerciement */}
          <div className="text-center pt-4">
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Merci pour votre soutien !
            </p>
          </div>
        </div>
      </div>

      {/* CSS pour l'animation */}
      <style>{`
        @keyframes fade-in-up {
          from {
            opacity: 0;
            transform: translateY(30px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        .animate-fade-in-up {
          animation: fade-in-up 0.3s ease-out;
        }
      `}</style>
    </div>
  )
}
