export default function Modal({ children, onClose, width }) {
  return (
    <div className="modal-overlay" onMouseDown={(e) => e.target === e.currentTarget && onClose?.()}>
      <div className="modal" style={width ? { width } : undefined}>
        {onClose && (
          <button className="modal-close" onClick={onClose} aria-label="Закрыть">
            ×
          </button>
        )}
        {children}
      </div>
    </div>
  );
}
