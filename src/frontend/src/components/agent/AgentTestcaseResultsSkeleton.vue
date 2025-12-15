<template>
  <div class="flex flex-col gap-2 h-full">
    <div class="flex justify-between items-center animate-pulse">
      <div class="flex justify-between items-center flex-1 px-2 py-2">
        <div class="h-5 bg-auxiliar-gray rounded w-48"></div>
        <div class="bg-pale rounded-xl px-2 py-1 flex flex-row items-center gap-5">
          <div class="flex flex-row items-center gap-2">
            <div class="h-4 w-8 bg-auxiliar-gray rounded"></div>
          </div>
          <div class="flex flex-row items-center gap-2">
            <div class="h-4 w-8 bg-auxiliar-gray rounded"></div>
          </div>
          <div class="flex flex-row items-center gap-2">
            <div class="h-4 w-8 bg-auxiliar-gray rounded"></div>
          </div>
          <div class="flex flex-row items-center gap-2">
            <div class="h-4 w-8 bg-auxiliar-gray rounded"></div>
          </div>
        </div>
      </div>
      <div class="flex flex-row items-center gap-2">
        <div class="h-8 w-8 bg-auxiliar-gray rounded"></div>
      </div>
    </div>
    <div class="flex flex-col gap-2 min-h-0 overflow-y-auto">
      <div v-for="i in 8" :key="i" class="border-1 border-auxiliar-gray rounded-xl px-3 py-2 shadow-xs min-h-[50px] animate-pulse">
        <div class="flex items-center justify-between h-full">
          <div class="h-5 bg-auxiliar-gray rounded" :class="[
            i % 3 === 0 ? 'w-48' : i % 3 === 1 ? 'w-56' : 'w-44'
          ]"></div>
          <div class="flex flex-row items-center gap-2">
            <div class="h-4 w-4 bg-auxiliar-gray rounded"></div>
            <div class="h-4 bg-auxiliar-gray rounded w-16"></div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
