"use client";

import { useState, useEffect, useRef } from "react";

export default function StreamingText({
  text,
  isStreaming,
}: {
  text: string;
  isStreaming: boolean;
}) {
  const [displayLen, setDisplayLen] = useState(0);
  const prevLenRef = useRef(0);

  // When not streaming, show full text immediately
  useEffect(() => {
    if (!isStreaming && text.length > 0) {
      setDisplayLen(text.length);
      prevLenRef.current = text.length;
    }
  }, [isStreaming, text]);

  // Typing animation: catch up to target text smoothly
  useEffect(() => {
    if (!isStreaming) return;
    if (displayLen >= text.length) return;

    const backlog = text.length - displayLen;
    // Adaptive speed: faster when more text is buffered
    const delay = backlog > 40 ? 4 : backlog > 15 ? 8 : 16;
    const step = backlog > 60 ? 4 : backlog > 30 ? 3 : backlog > 10 ? 2 : 1;

    const timer = setTimeout(() => {
      setDisplayLen((prev) => Math.min(prev + step, text.length));
    }, delay);

    return () => clearTimeout(timer);
  }, [text, isStreaming, displayLen]);

  if (!isStreaming && displayLen >= text.length) {
    return <>{text}</>;
  }

  return (
    <>
      {text.slice(0, displayLen)}
      {isStreaming && (
        <span className="inline-block w-[2px] h-[1em] bg-primary animate-blink ml-[1px] align-text-bottom" />
      )}
    </>
  );
}
