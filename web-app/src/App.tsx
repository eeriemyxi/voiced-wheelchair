import { useState } from "react";

import { LuBadgeInfo } from "react-icons/lu";
import { MdKeyboardVoice } from "react-icons/md";

function App() {
  return (
    <div className="flex flex-col w-full h-dvh justify-center items-center gap-80">
      <div className="flex flex-col border-3 p-10 border-border rounded-full bg-bg drop-shadow-xl">
        <h1 className="text-3xl font-medium font-nunito text-text-primary">
          Wheelchair Controller
        </h1>
        <p className="font-nunito text-text-primary/90">
          Control your wheelchair via natural speech
        </p>
      </div>
      <div className="flex flex-col justify-center items-center gap-5">
        <button className="bg-accent p-5 rounded-full text-text-inverse cursor-pointer hover:bg-accent/80 drop-shadow-lg">
          <MdKeyboardVoice size={20} />
        </button>
        <div className="flex justify-center items-center gap-2 text-sm border-2 p-2 border-blue-500 drop-shadow-blue-500/20 text-blue-500/90 rounded-full bg-bg drop-shadow-lg">
          <LuBadgeInfo size={25} />
          <p className="font-nunito">
            Tap this button to instruct your wheelchair :)
          </p>
        </div>
      </div>
    </div>
  );
}

export default App;
