<!-- Svelte 5 test file -->
<script context="module">
    export function moduleFunction() {
        return 'module scope';
    }
</script>

<script>
    import { onMount } from 'svelte';
    
    let { name = 'World' } = $props();
    let count = $state(0);
    let items = $state([]);
    
    onMount(async () => {
        const response = await fetch('/api/items');
        items = await response.json();
    });
    
    function handleClick() {
        count += 1;
    }
    
    class DataStore {
        data = $state([]);
        
        add(item) {
            this.data.push(item);
        }
    }
    
    let store = new DataStore();
</script>

<style>
    h1 {
        color: purple;
    }
    
    .counter {
        padding: 1rem;
        border: 1px solid #ccc;
    }
</style>

<main>
    <h1>Hello {name}!</h1>
    <div class="counter">
        <p>Count: {count}</p>
        <button onclick={handleClick}>
            Increment
        </button>
    </div>
    
    {#each items as item}
        <p>{item.name}</p>
    {/each}
</main>