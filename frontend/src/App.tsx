import { useState, useEffect, useRef } from "react";
import { create } from "zustand";
import { persist } from "zustand/middleware";
import { Dialog, Switch } from "@headlessui/react";

import { HiDotsHorizontal } from "react-icons/hi";
import { LuBadgeInfo } from "react-icons/lu";
import { MdKeyboardVoice, MdSettings, MdClose, MdCancel, MdCheckCircle, MdError } from "react-icons/md";
import SpeechRecognition, {
  useSpeechRecognition,
} from "react-speech-recognition";

// Define your realtime trigger words here
const REALTIME_COMMANDS = ["forward", "backward", "left", "right", "stop"];

const useSettingsStore = create(
  persist(
    (set) => ({
      useAi: false,
      autoSend: false,
      voiceReset: false,
      voiceCancel: false,
      realtimeCommand: false,
      toggleUseAi: () => set((state) => ({ useAi: !state.useAi })),
      toggleAutoSend: () => set((state) => ({ autoSend: !state.autoSend })),
      toggleVoiceReset: () => set((state) => ({ voiceReset: !state.voiceReset })),
      toggleVoiceCancel: () => set((state) => ({ voiceCancel: !state.voiceCancel })),
      toggleRealtimeCommand: () => set((state) => ({ realtimeCommand: !state.realtimeCommand })),
    }),
    {
      name: "wheelchair-settings",
    }
  )
);

function App() {
  const {
    transcript,
    listening,
    resetTranscript,
    browserSupportsSpeechRecognition,
  } = useSpeechRecognition();

  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [notification, setNotification] = useState(null); // { type: 'success' | 'error', message: '...' }
  const notificationTimeoutRef = useRef(null);

  const { 
    useAi, 
    autoSend, 
    voiceReset, 
    voiceCancel,
    realtimeCommand,
    toggleUseAi, 
    toggleAutoSend, 
    toggleVoiceReset, 
    toggleVoiceCancel,
    toggleRealtimeCommand
  } = useSettingsStore();

  // Helper to show notification and auto-hide it after 3 seconds
  const showNotification = (type, message) => {
    setNotification({ type, message });
    if (notificationTimeoutRef.current) {
      clearTimeout(notificationTimeoutRef.current);
    }
    notificationTimeoutRef.current = setTimeout(() => {
      setNotification(null);
    }, 3000);
  };

  const sendInstruction = async (textToSend) => {
    // 1. Prevent sending if instruction is empty
    if (!textToSend || !textToSend.trim()) {
      return; 
    }
    
    const url = new URL("/api/control", window.location.origin);
    url.searchParams.set("prompt", textToSend.trim());
    url.searchParams.set("use_ai", useAi.toString());

    // 2. Setup AbortController for a 2-second timeout
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 2000);

    try {
      // 3. Make the asynchronous fetch request
      const response = await fetch(url.toString(), { 
        method: 'POST',
        signal: controller.signal // Attach the abort signal
      });

      clearTimeout(timeoutId); // Clear timeout if it succeeds before 2s

      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }

      console.log(`Sent to backend: "${textToSend.trim()}" | use_ai: ${useAi}`);
      showNotification('success', `Command sent: "${textToSend.trim()}"`);

    } catch (error) {
      clearTimeout(timeoutId); // Ensure timeout is cleared on error too

      if (error.name === 'AbortError') {
        console.error("Request timed out");
        showNotification('error', 'Request timed out (exceeded 2 seconds).');
      } else {
        console.error("Failed to send instruction", error);
        showNotification('error', 'Failed to send instruction.');
      }
    }
  };

  useEffect(() => {
    if (!transcript) return;

    // Realtime Command Check
    if (realtimeCommand) {
      const matchedCommand = REALTIME_COMMANDS.find(cmd => 
        new RegExp(`\\b(${cmd})\\s*$`, 'i').test(transcript)
      );
      
      if (matchedCommand) {
        sendInstruction(matchedCommand);
        resetTranscript();
        return;
      }
    }

    if (voiceCancel && /\b(cancel)\s*$/i.test(transcript)) {
      SpeechRecognition.stopListening();
      resetTranscript();
      return;
    }

    if (voiceReset && /\b(reset)\s*$/i.test(transcript)) {
      resetTranscript();
      return;
    }

    if (autoSend && /\b(send)\s*$/i.test(transcript)) {
      const cleanPrompt = transcript.replace(/\b(send)\s*$/i, "").trim();
      sendInstruction(cleanPrompt);
      resetTranscript();
    }
  }, [transcript, autoSend, voiceReset, voiceCancel, realtimeCommand, resetTranscript]);

  if (!browserSupportsSpeechRecognition) {
    return <span className="p-5 font-nunito">Browser doesn't support speech recognition.</span>;
  }

  return (
    <div className="relative flex flex-col w-full min-h-dvh justify-center items-center gap-10 md:gap-16 px-4 py-10 bg-bg">
      
      {/* --- NOTIFICATION TOAST --- */}
      {notification && (
        <div className={`fixed top-5 left-1/2 -translate-x-1/2 z-50 flex items-center gap-2 px-6 py-3 rounded-full drop-shadow-xl font-nunito text-sm transition-all animate-in slide-in-from-top-4 fade-in ${
          notification.type === 'success' 
            ? 'bg-green-100 text-green-800 border-2 border-green-300' 
            : 'bg-red-100 text-red-800 border-2 border-red-300'
        }`}>
          {notification.type === 'success' ? <MdCheckCircle size={20} /> : <MdError size={20} />}
          <span>{notification.message}</span>
        </div>
      )}

      <button
        onClick={() => setIsSettingsOpen(true)}
        className="absolute top-5 right-5 md:top-8 md:right-8 p-3 bg-bg border-2 border-border text-text-primary rounded-full drop-shadow-md hover:bg-border/20 transition-colors"
        aria-label="Open Settings"
      >
        <MdSettings size={24} />
      </button>

      <div className="flex flex-col border-3 p-8 md:p-10 border-border rounded-full bg-bg drop-shadow-xl w-full max-w-md text-center">
        <h1 className="text-2xl md:text-3xl font-medium font-nunito text-text-primary mb-2">
          Wheelchair Controller
        </h1>
        <p className="font-nunito text-sm md:text-base text-text-primary/90">
          Control your wheelchair via natural speech
        </p>
      </div>

      <div className="p-4 md:p-6 border-2 rounded-full border-yellow-400 text-yellow-500/90 bg-bg drop-shadow-[0_10px_15px_rgba(234,179,8,0.2)] w-full max-w-lg min-h-[80px] flex items-center justify-center text-center transition-all">
        <p className="font-nunito">{transcript || "No instructions yet..."}</p>
      </div>

      <div className="flex flex-col justify-center items-center gap-6 md:gap-8">
        <div className="flex items-center gap-4">
          
          <button
            className={`${
              listening ? "bg-accent/80 animate-pulse" : "bg-accent hover:bg-accent/90"
            } p-6 md:p-8 rounded-full text-text-inverse cursor-pointer drop-shadow-xl transition-all`}
            onClick={() => {
              if (!listening) {
                resetTranscript();
                SpeechRecognition.startListening({
                  continuous: true,
                  language: "en-IN",
                });
              } else {
                SpeechRecognition.stopListening();
                sendInstruction(transcript);
                resetTranscript();
              }
            }}
          >
            {listening ? (
              <HiDotsHorizontal size={32} />
            ) : (
              <MdKeyboardVoice size={32} />
            )}
          </button>

          {listening && (
            <button
              onClick={() => {
                SpeechRecognition.stopListening();
                resetTranscript();
              }}
              className="bg-red-500/70 p-4 md:p-5 rounded-full text-white cursor-pointer hover:bg-red-600 drop-shadow-lg transition-colors"
              aria-label="Cancel recording"
            >
              <MdCancel size={28} />
            </button>
          )}
        </div>

        <div className="flex justify-center items-center gap-2 text-xs md:text-sm border-2 p-3 px-5 border-blue-500 text-blue-500/90 rounded-full bg-bg drop-shadow-[0_10px_15px_rgba(59,130,246,0.2)]">
          <LuBadgeInfo size={20} className="shrink-0" />
          <p className="font-nunito">
            {listening ? "Speak your command or tap the red button to cancel." : "Tap the mic button to instruct your wheelchair."}
          </p>
        </div>
      </div>

      <Dialog
        open={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        className="relative z-50"
      >
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm" aria-hidden="true" />
        
        <div className="fixed inset-0 flex items-center justify-center p-4">
          <Dialog.Panel className="w-full max-w-sm rounded-3xl bg-bg border-2 border-border p-6 md:p-8 drop-shadow-2xl">
            <div className="flex justify-between items-center mb-6">
              <Dialog.Title className="text-xl font-nunito font-medium text-text-primary">
                Settings
              </Dialog.Title>
              <button 
                onClick={() => setIsSettingsOpen(false)}
                className="text-text-primary/60 hover:text-text-primary transition-colors"
              >
                <MdClose size={24} />
              </button>
            </div>

            <div className="flex flex-col gap-6">
              <div className="flex items-center justify-between">
                <div className="pr-4">
                  <h3 className="font-nunito text-text-primary font-medium">Use AI Processing</h3>
                  <p className="text-sm font-nunito text-text-primary/70">Enable backend NLP interpretation</p>
                </div>
                <Switch
                  checked={useAi}
                  onChange={toggleUseAi}
                  className={`${
                    useAi ? "bg-accent" : "bg-gray-400"
                  } relative inline-flex h-6 w-11 items-center rounded-full transition-colors shrink-0`}
                >
                  <span className={`${
                    useAi ? "translate-x-6" : "translate-x-1"
                  } inline-block h-4 w-4 transform rounded-full bg-white transition-transform`}
                  />
                </Switch>
              </div>

              <div className="flex items-center justify-between">
                <div className="pr-4">
                  <h3 className="font-nunito text-text-primary font-medium">Realtime Command</h3>
                  <p className="text-sm font-nunito text-text-primary/70">Execute directional commands instantly</p>
                </div>
                <Switch
                  checked={realtimeCommand}
                  onChange={toggleRealtimeCommand}
                  className={`${
                    realtimeCommand ? "bg-accent" : "bg-gray-400"
                  } relative inline-flex h-6 w-11 items-center rounded-full transition-colors shrink-0`}
                >
                  <span className={`${
                    realtimeCommand ? "translate-x-6" : "translate-x-1"
                  } inline-block h-4 w-4 transform rounded-full bg-white transition-transform`}
                  />
                </Switch>
              </div>

              <div className="flex items-center justify-between">
                <div className="pr-4">
                  <h3 className="font-nunito text-text-primary font-medium">Voice Send</h3>
                  <p className="text-sm font-nunito text-text-primary/70">Say "send" to execute</p>
                </div>
                <Switch
                  checked={autoSend}
                  onChange={toggleAutoSend}
                  className={`${
                    autoSend ? "bg-accent" : "bg-gray-400"
                  } relative inline-flex h-6 w-11 items-center rounded-full transition-colors shrink-0`}
                >
                  <span className={`${
                    autoSend ? "translate-x-6" : "translate-x-1"
                  } inline-block h-4 w-4 transform rounded-full bg-white transition-transform`}
                  />
                </Switch>
              </div>

              <div className="flex items-center justify-between">
                <div className="pr-4">
                  <h3 className="font-nunito text-text-primary font-medium">Voice Reset</h3>
                  <p className="text-sm font-nunito text-text-primary/70">Say "reset" to clear command</p>
                </div>
                <Switch
                  checked={voiceReset}
                  onChange={toggleVoiceReset}
                  className={`${
                    voiceReset ? "bg-accent" : "bg-gray-400"
                  } relative inline-flex h-6 w-11 items-center rounded-full transition-colors shrink-0`}
                >
                  <span className={`${
                    voiceReset ? "translate-x-6" : "translate-x-1"
                  } inline-block h-4 w-4 transform rounded-full bg-white transition-transform`}
                  />
                </Switch>
              </div>

              <div className="flex items-center justify-between">
                <div className="pr-4">
                  <h3 className="font-nunito text-text-primary font-medium">Voice Cancel</h3>
                  <p className="text-sm font-nunito text-text-primary/70">Say "cancel" to stop recording</p>
                </div>
                <Switch
                  checked={voiceCancel}
                  onChange={toggleVoiceCancel}
                  className={`${
                    voiceCancel ? "bg-accent" : "bg-gray-400"
                  } relative inline-flex h-6 w-11 items-center rounded-full transition-colors shrink-0`}
                >
                  <span className={`${
                    voiceCancel ? "translate-x-6" : "translate-x-1"
                  } inline-block h-4 w-4 transform rounded-full bg-white transition-transform`}
                  />
                </Switch>
              </div>
            </div>
          </Dialog.Panel>
        </div>
      </Dialog>
    </div>
  );
}

export default App;