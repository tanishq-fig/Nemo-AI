import React from 'react';
import { motion } from 'framer-motion';

interface BubbleProps {
  delay?: number;
  duration?: number;
  size?: number;
  left?: string;
}

const Bubble: React.FC<BubbleProps> = ({ 
  delay = 0, 
  duration = 8, 
  size = 40, 
  left = '50%' 
}) => {
  return (
    <motion.div
      className="absolute rounded-full bg-white/10 backdrop-blur-sm"
      style={{
        width: size,
        height: size,
        left: left,
        bottom: -100,
      }}
      animate={{
        y: [0, -window.innerHeight - 100],
        opacity: [0, 0.8, 0.8, 0],
        scale: [1, 1.5],
      }}
      transition={{
        duration: duration,
        repeat: Infinity,
        delay: delay,
        ease: 'easeInOut',
      }}
    />
  );
};

export const BubbleBackground: React.FC = () => {
  return (
    <div className="fixed inset-0 overflow-hidden pointer-events-none">
      <Bubble delay={0} duration={10} size={30} left="10%" />
      <Bubble delay={2} duration={12} size={50} left="30%" />
      <Bubble delay={4} duration={9} size={40} left="50%" />
      <Bubble delay={1} duration={11} size={35} left="70%" />
      <Bubble delay={3} duration={13} size={45} left="85%" />
      <Bubble delay={5} duration={10} size={25} left="20%" />
      <Bubble delay={7} duration={14} size={55} left="60%" />
    </div>
  );
};
