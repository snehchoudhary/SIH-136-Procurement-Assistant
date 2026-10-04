import { AnimatePresence, motion } from 'framer-motion';
import { X } from 'lucide-react';

type DrawerProps = {
  open: boolean;
  onClose: () => void;
  children: React.ReactNode;
};

export function Drawer({ open, onClose, children }: DrawerProps) {
  return (
    <AnimatePresence>
      {open ? (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-40 flex justify-end bg-text/60"
          onClick={onClose}
        >
          <motion.aside
            initial={{ x: 380 }}
            animate={{ x: 0 }}
            exit={{ x: 380 }}
            transition={{ duration: 0.2 }}
            className="h-full w-full max-w-md border-l border-border bg-surface p-6 shadow-2xl"
            onClick={(event) => event.stopPropagation()}
          >
            {children}
          </motion.aside>
        </motion.div>
      ) : null}
    </AnimatePresence>
  );
}
