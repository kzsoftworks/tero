<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { ref, onMounted, watch, computed } from 'vue'
import { TeamRoleStatus, MY_TEAM_ID, TeamUser } from '@/services/api'
import { ApiService } from '@/services/api'
import { useErrorHandler } from '@/composables/useErrorHandler'
import { useDebounce } from '@/composables/useDebounce'
import { Role } from '@/services/api'
import auth from '@/services/auth'

const { t } = useI18n()
const { handleError } = useErrorHandler()
const api = new ApiService()

const props = defineProps<{
  fromDate: Date
  toDate: Date
  teamId: number
  compactDisplay?: boolean
}>()

const emit = defineEmits<{
  (e: 'updateUsers'): void
  (e: 'isSaving', value: boolean): void
  (e: 'selectedTeamChanged', teamId: number): void
}>()

const loading = ref<boolean>(false)
const users = ref<TeamUser[]>([])
const userPage = ref<number>(1)
const pageSize = 20
const loadingMoreUsers = ref<boolean>(false)
const hasMoreUsers = ref<boolean>(true)
const isSearchingUser = ref<boolean>(false)
const searchUser = ref<string>('')
const roleNames = computed<Record<string, string>>(() => ({
  [Role.TEAM_OWNER]: t('teamOwner'),
  [Role.TEAM_MEMBER]: t('teamMember'),
  [Role.TEAM_EDITOR]: t('teamEditor')
}))

const showAddUserModal = ref<boolean>(false)
const editingRoleRows = ref<number[]>([])
const selectedUserToDelete = ref<TeamUser | null>(null)
const showDeleteUserModal = computed(() => selectedUserToDelete.value !== null)
const selectedUserModalHeader = computed(() => t(`${buildDeleteUserKey()}Title`, { name: selectedUserToDelete.value?.name }))
const selectedUserModalText = computed(() => t(`${buildDeleteUserKey()}Text`, { name: selectedUserToDelete.value?.name }))

const buildDeleteUserKey = (): string => {
  const status = selectedUserToDelete.value?.roleStatus
  if (status === TeamRoleStatus.PENDING) {
    return 'cancelInvitation'
  }
  if (status === TeamRoleStatus.REJECTED) {
    return 'deleteInvitation'
  }
  return 'deleteUser'
}

onMounted(async () => {
  await loadUsersData()
})

const loadUsersData = async () => {
  try {
    loading.value = true
    await loadData()
  } catch (error) {
    handleError(error)
  } finally {
    loading.value = false
  }
}

const loadData = async () => {
  userPage.value = 1
  const resp = await api.findTeamUsers(props.teamId, pageSize + 1, 0, searchUser.value)
  users.value = resp.slice(0, pageSize)

  hasMoreUsers.value = resp.length === pageSize + 1
  isSearchingUser.value = false
}

const handleLoadMoreUsers = async () => {
  try {
    loadingMoreUsers.value = true
    userPage.value++
    const moreUsers = await api.findTeamUsers(props.teamId, pageSize + 1, (userPage.value - 1) * pageSize, searchUser.value)
    users.value = [...users.value, ...moreUsers.slice(0, pageSize)]
    hasMoreUsers.value = moreUsers.length === pageSize + 1
  } catch (error) {
    handleError(error)
  } finally {
    loadingMoreUsers.value = false
  }
}

watch(
  () => searchUser.value,
  async () => {
    isSearchingUser.value = true
    performDebouncedUserSearch()
  }
)

const performDebouncedUserSearch = useDebounce(loadData)

watch(
  () => props.teamId,
  async () => {
    await loadUsersData()
  }
)

const handleEditUserRole = (userId: number) => {
  editingRoleRows.value.push(userId)
}

const checkCurrentUser = async (username: string) => {
  const currentUser = (await auth.getUser())?.profile?.email
  return currentUser === username
}

const handleRoleChange = async (user: TeamUser) => {
  emit('isSaving', true)
  try {
    await api.updateUserRoleInTeam(props.teamId, user.id!, user.role as Role)

    if ((await checkCurrentUser(user.username)) && user.role === Role.TEAM_MEMBER) {
      emit('selectedTeamChanged', MY_TEAM_ID)
    }
  } catch (error) {
    handleError(error)
  } finally {
    editingRoleRows.value = editingRoleRows.value.filter((id) => id !== user.id)
    emit('isSaving', false)
  }
}

const handleDeleteUser = async (user: TeamUser) => {
  selectedUserToDelete.value = user
}

const handleCloseDeleteUserModal = () => {
  selectedUserToDelete.value = null
}

const handleConfirmDeleteUser = async () => {
  try {
    await api.deleteUserFromTeam(props.teamId, selectedUserToDelete.value!.id!)

    if (await checkCurrentUser(selectedUserToDelete.value!.username)) {
      emit('selectedTeamChanged', MY_TEAM_ID)
    } else {
      emit('updateUsers')
    }
  } catch (error) {
    handleError(error)
  } finally {
    handleCloseDeleteUserModal()
    await loadUsersData()
  }
}
</script>

<template>
  <div v-if="loading" class="w-full h-full">
    <div class="bg-pale rounded-lg p-4 animate-pulse">
      <div class="h-5 bg-auxiliar-gray rounded w-32 mb-6"></div>
      <div class="space-y-4">
        <div v-for="i in pageSize" :key="i" class="flex justify-between items-center py-2">
          <div class="h-4 bg-auxiliar-gray rounded w-32"></div>
          <div class="h-4 bg-auxiliar-gray rounded w-16"></div>
        </div>
      </div>
    </div>
  </div>
  <DashboardCard v-else :title="t('usersTitle')" :compact-display="compactDisplay">
    <template #actions>
      <div class="flex flex-grow justify-end items-center gap-4">
        <SimpleButton shape="square" @click="showAddUserModal = true"><IconPlus />{{ t('addUser') }}</SimpleButton>
        <InteractiveInput v-model="searchUser" :placeholder="t('searchUser')" start-icon="IconSearch" :loading="isSearchingUser" class="w-full max-w-1/2" v-if="!compactDisplay" />
      </div>
    </template>
    <DataTable :value="users" size="small" :show-headers="false">
      <Column field="userName">
        <template #body="slotProps">
          <div class="flex items-center gap-1 h-8">
            <span :class="{ 'text-light-gray line-through': slotProps.data.roleStatus === TeamRoleStatus.REJECTED }">
              {{ slotProps.data.name || slotProps.data.username }}
            </span>
          </div>
        </template>
      </Column>
      <Column field="role" class="w-15">
        <template #body="slotProps">
          <div v-if="(slotProps.data.roleStatus == TeamRoleStatus.ACCEPTED && slotProps.data.verified) || editingRoleRows.includes(slotProps.data.id)" class="flex items-center justify-end">
            <span v-if="!editingRoleRows.includes(slotProps.data.id)" class="block w-full text-right text-light-gray">{{ roleNames[slotProps.data.role as Role] }}</span>
            <Select v-else v-model="slotProps.data.role" :options="Object.entries(roleNames).map(([key, value]) => ({ label: value, value: key }))" option-label="label" option-value="value" @change="handleRoleChange(slotProps.data)" />
          </div>
          <div v-else class="flex items-center w-full justify-end">
            <SimpleTag v-if="slotProps.data.roleStatus === TeamRoleStatus.REJECTED" :text="t('rejectedInvitation')" class="bg-pale !text-light-gray" />
            <SimpleTag v-else-if="slotProps.data.roleStatus === TeamRoleStatus.PENDING || !slotProps.data.verified" :text="t('pendingInvitation')" />
          </div>
        </template>
      </Column>
      <Column field="" class="w-10">
        <template #body="slotProps">
          <DashboardUserMenu :user="slotProps.data" :team-id="props.teamId" @edit-user-role="handleEditUserRole(slotProps.data.id)" @delete-user="handleDeleteUser(slotProps.data)" />
        </template>
      </Column>
    </DataTable>
    <span v-if="users.length === 0" class="text-light-gray">
      {{ t('noUsersFound') }}
    </span>
    <template #footer>
      <SimpleButton v-if="hasMoreUsers" :disabled="loadingMoreUsers" @click="handleLoadMoreUsers" shape="rounded" shadow="gradient">
        <span v-if="loadingMoreUsers">{{ t('loadingMoreUsers') }}</span>
        <span v-else>{{ t('loadMoreUsers') }}</span>
      </SimpleButton>
    </template>
  </DashboardCard>
  <DashboardAddUserModal v-model:show-modal="showAddUserModal" :team-id="props.teamId" @users-added="loadUsersData" />
  <Dialog
    :visible="showDeleteUserModal"
    :header="selectedUserModalHeader"
    :modal="true"
    :closable="false"
    :draggable="false"
    :dismissable-mask="true"
    :close-on-escape="true"
    @hide="handleCloseDeleteUserModal"
    @keydown.esc="handleCloseDeleteUserModal"
  >
    <p>{{ selectedUserModalText }}</p>
    <template #footer>
      <SimpleButton @click="handleCloseDeleteUserModal" shape="square">{{ t('cancel') }}</SimpleButton>
      <SimpleButton @click="handleConfirmDeleteUser" shape="square" variant="error">
        {{ selectedUserToDelete?.roleStatus === TeamRoleStatus.ACCEPTED ? t('delete') : t('confirm') }}
      </SimpleButton>
    </template>
  </Dialog>
</template>

<i18n lang="json">
{
  "en": {
    "usersTitle": "Users",
    "loadingMoreUsers": "Loading more users...",
    "loadMoreUsers": "Load more users",
    "searchUser": "Search user",
    "noUsersFound": "No users found",
    "teamOwner": "Leader",
    "teamMember": "Member",
    "teamEditor": "Editor",
    "addUser": "Add",
    "cancel": "Cancel",
    "delete": "Remove",
    "pendingInvitation": "Pending",
    "rejectedInvitation": "Rejected",
    "cancelInvitationTitle": "Cancel invitation to {name}",
    "deleteInvitationTitle": "Delete invitation to {name}",
    "deleteUserTitle": "Remove user {name}",
    "cancelInvitationText": "Are you sure you want to cancel the invitation to this user?",
    "deleteInvitationText": "Are you sure you want to delete the invitation to this user?",
    "deleteUserText": "Are you sure you want to remove this user from the team?",
    "confirm": "Confirm"
  },
  "es": {
    "usersTitle": "Usuarios",
    "loadingMoreUsers": "Cargando más usuarios...",
    "loadMoreUsers": "Cargar más usuarios",
    "searchUser": "Buscar usuario",
    "noUsersFound": "No se encontraron usuarios",
    "teamOwner": "Líder",
    "teamMember": "Miembro",
    "teamEditor": "Editor",
    "addUser": "Agregar",
    "cancel": "Cancelar",
    "delete": "Remover",
    "pendingInvitation": "Pendiente",
    "rejectedInvitation": "Rechazada",
    "cancelInvitationTitle": "Cancelar invitación a {name}",
    "deleteInvitationTitle": "Eliminar invitación a {name}",
    "deleteUserTitle": "Remover usuario {name}",
    "cancelInvitationText": "¿Estás seguro de querer cancelar la invitación a este usuario?",
    "deleteInvitationText": "¿Estás seguro de querer eliminar la invitación a este usuario?",
    "deleteUserText": "¿Estás seguro de querer remover este usuario del equipo?",
    "confirm": "Confirmar"
  }
}
</i18n>
